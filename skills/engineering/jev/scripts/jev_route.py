"""jev.py route: a second, independent pick of role and effort for each task in a plan.

Usage: jev.py route PLAN.md [--out FILE]

Reads the task table every plan ends in (workflow-map's task-table format), asks Jev to place
each task on the role-and-effort rows of role-orchestrator, and compares that with the role
and effort the plan already wrote. Prints a verdict per task; never dispatches anything.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from jev_client import JevAuthError, JevError, api_key, ask, is_allowed, load_config

_WORKERS = 8
_SURE = 0.75

# Mirrors role-orchestrator's "Choosing role and effort per task" table and the effort rules
# in its references/model-map.md. Change them together; the options must not overlap.
# Designer effort follows model-map (a root-cause hunt is medium): adding "a hard root-cause
# hunt" to designer-high dropped the pilot from 11 of 12 to 8. Rerun the pilot after any edit.
OPTIONS = {
    "chore-low": "A tiny mechanical edit the instructions fully decide: a rename, a version bump, "
                 "an approved copy swap, a lint fix. One check.",
    "chore-medium": "A change the instructions fully decide but spread over several files or needing "
                    "care to apply: fixture updates, guide edits, review nits with a named fix, cleanup. "
                    "No choice is left to make.",
    "worker-medium": "A scoped fix or feature whose cause is known, with no visual output and no "
                     "data-loss risk. It needs judgment while coding.",
    "worker-high": "A scoped fix or feature whose cause is known, but with visual output (layout, UI "
                   "states, motion), a rebase with real conflicts, or code whose bugs lose data or "
                   "money: payments, billing, ledgers, migrations, engines and contracts.",
    "designer-medium": "The cause is unknown: an investigation or root-cause hunt with no visual output.",
    "designer-high": "A spec, board, audit or architecture to write, or design work with visual "
                     "output. No shipped behaviour.",
    "reviewer-high": "Review a finished branch before it merges. Read only.",
    "product-medium": "A copy, positioning, pricing or onboarding question to answer. No code.",
    "unclear": "The task is too vague to place, or it belongs to an agent specific to one project.",
}
# Escalations (xhigh after a miss at high, designer after a worker failed twice) depend on
# history that task text does not carry, so they stay the orchestrator's call.
# Claude Code column of role-orchestrator's references/model-map.md; a test checks the drift.
MODELS = {"chore": "haiku", "worker": "sonnet", "designer": "opus", "reviewer": "opus", "product": "opus"}
QUESTION = {
    "route": {
        "type": "choice",
        "instructions": (
            "Which role and effort should carry out `task`? Judge from what it asks, the files it "
            "writes and the check that proves it: how much of the change the description already "
            "decides, whether the cause is known, and whether it has visual output or data-loss risk."
        ),
        "criteria": OPTIONS,
    }
}


REQUIRED = {"task", "files it writes", "role", "effort", "check"}


class TableError(ValueError):
    pass


def split_row(line: str) -> list[str]:
    # \| is how a cell holds a pipe; splitting on it would shift every later column.
    cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
    return [cell.strip().replace("\\|", "|") for cell in cells]


def read_table(text: str) -> list[dict]:
    """Rows of the last task table (workflow-map's columns) outside a code fence."""
    table: list[dict] = []
    header: list[str] | None = None
    fenced = False
    for line in text.split("\n"):
        if line.lstrip().startswith(("```", "~~~")):
            fenced, header = not fenced, None
            continue
        if fenced or not line.lstrip().startswith("|"):
            header = None
            continue
        cells = split_row(line)
        if header is None:
            names = [cell.lower() for cell in cells]
            if REQUIRED <= set(names):
                header, table = names, []
            continue
        if all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        if len(cells) != len(header):
            raise TableError(f"a row has {len(cells)} cells, the header {len(header)}: {line.strip()[:80]}")
        table.append(dict(zip(header, cells)))
    return table


def option_of(role: str, effort: str) -> str:
    """`worker`, "medium (default)" -> worker-medium."""
    words = effort.replace("`", "").lower().split()
    return f"{role.replace('`', '').strip().lower()}-{words[0] if words else ''}"


def verdict(planned: str, picked: str, confidence: float) -> str:
    role = planned.rsplit("-", 1)[0]  # a project agent may be called worker-ui
    if role not in MODELS:
        return "project agent: yours to judge"
    if picked == planned:
        return "sure" if confidence >= _SURE else "sure, but close"
    if picked.rsplit("-", 1)[0] == role:
        return "check the effort"
    return "UNSURE: show both to the human"


def cell(text: object) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def repo_root(path: Path) -> str:
    try:
        result = subprocess.run(["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
                                capture_output=True, text=True, check=False)
    except OSError:  # no git: the plan's own folder is what must be allowed
        return str(path.parent)
    return result.stdout.strip() if result.returncode == 0 else str(path.parent)


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="jev.py route", description=__doc__.splitlines()[0])
    parser.add_argument("plan", type=Path)
    parser.add_argument("--out", type=Path, help="write every pick with its probabilities as JSON")
    args = parser.parse_args(argv)

    plan = args.plan.resolve()
    root = repo_root(plan)
    if not is_allowed(root, load_config()):
        print(f"jev route: {root} is not in hooks_allow, and route sends the plan's tasks to "
              "TypeSafe. Add it with: jev.py allow FOLDER", file=sys.stderr)
        return 2
    try:
        rows = read_table(plan.read_text())
    except (OSError, TableError) as error:
        print(f"jev route: {error}", file=sys.stderr)
        return 2
    if not rows:
        print("jev route: no task table in the plan (columns: Task, Files it writes, Role, Effort, Check)",
              file=sys.stderr)
        return 2
    print(f"jev route: {len(rows)} task(s) read from the table", file=sys.stderr)
    key = api_key()

    def judge(row: dict) -> dict:
        # The plan's own role and effort stay out of the state, so Jev reads the evidence, not the answer.
        state = {"task": row.get("task", ""), "files": row.get("files it writes", ""),
                 "check": row.get("check", "")}
        try:
            answer = ask(state, QUESTION, key=key)["answers"]["route"]
            return {**row, "picked": answer["choice"], "confidence": float(answer["confidence"]),
                    "probabilities": answer.get("probabilities", {})}
        except JevAuthError:
            raise
        except (JevError, KeyError, TypeError, ValueError) as error:
            return {**row, "error": str(error)[:200]}

    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        results = list(pool.map(judge, rows))

    print("| # | Task | Plan | Jev | Model | Verdict |")
    print("| --- | --- | --- | --- | --- | --- |")
    for result in results:
        planned = option_of(result.get("role", ""), result.get("effort", ""))
        if "error" in result:
            print(f"| {cell(result.get('#', ''))} | {cell(result.get('task', '')[:60])} | {cell(planned)} "
                  f"| N/A | N/A | FAILED: {cell(result['error'])} |")
            continue
        picked, confidence = result["picked"], result["confidence"]
        result["verdict"] = verdict(planned, picked, confidence)
        model = MODELS.get(picked.split("-")[0], "N/A")
        print(f"| {cell(result.get('#', ''))} | {cell(result.get('task', '')[:60])} | {cell(planned)} "
              f"| {picked} ({confidence:.2f}) | {model} | {result['verdict']} |")
    if args.out:
        args.out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    return 1 if any("error" in result for result in results) else 0
