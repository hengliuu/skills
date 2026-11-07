"""jev.py gate: run the diff quality gates (scope, comments, algorithm) over a change.

Usage: jev.py gate [--base REF] [--request TEXT | --request-file FILE] [--out FILE] [PATH ...]

Without --base it reads the uncommitted change (git diff HEAD, plus untracked files). With
--base it reads everything since the merge base with REF, uncommitted work included. It
prints leads to check and never edits anything.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from jev_client import JevAuthError, JevError, api_key, ask, is_allowed, load_config

_WORKERS = 8
_MAX_ITEMS = 80
_MAX_STATE_CHARS = 6000
_LEAD, _UNSURE = 0.6, 0.4
LOCKFILES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lockb", "Cargo.lock", "go.sum",
             "poetry.lock", "uv.lock", "Pipfile.lock", "Gemfile.lock", "composer.lock", "flake.lock"}
GENERATED = (".min.js", ".min.css", ".map")
_HASH, _SLASH = ("#",), ("//", "/*", "*")
COMMENT_PREFIXES = {
    **dict.fromkeys((".py", ".sh", ".bash", ".zsh", ".rb", ".ex", ".exs", ".yaml", ".yml", ".toml", ".tf"), _HASH),
    **dict.fromkeys((".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue", ".svelte", ".go", ".rs", ".java",
                     ".kt", ".swift", ".c", ".h", ".cc", ".cpp", ".cs", ".dart", ".php", ".scala"), _SLASH),
    **dict.fromkeys((".sql", ".lua"), ("--",)),
}
CONFIG_SUFFIXES = {".yaml", ".yml", ".toml"}
DIRECTIVE = re.compile(r"//\s*(go:|@ts-|eslint|nolint|#(end)?region)|#\s*(noqa|type:|pylint:|fmt:|pragma)|#!")
# Test inputs are tiny, so a linear scan there costs nothing; the first live run flagged one.
TEST_PATH = re.compile(
    r"(^|/)(?i:tests?|__tests__|__mocks__|spec|e2e|testdata|fixtures)/"
    r"|(^|/)(test_[^/]*|conftest\.py)$|[._-](test|spec)\.[^/]+$|_test\.go$|[a-z0-9]Tests?\.(java|kt|cs|swift|scala)$"
)
LOOP = re.compile(r"\b(for|while)\b|\.(map|forEach|filter|reduce|some|every|find)\(|\brange\(|\.iter\(\)")
_CONTEXT = 3
_MAX_COMMENT_CHARS = 2000

QUESTIONS = {
    "scope": {
        "type": "noul",
        "instructions": (
            "`hunk` is one part of a change to `file`, in unified diff form (lines starting with + "
            "were added, - removed). Does this part serve `request`, directly or as something the "
            "request needs (a test, an import, an updated caller)?"
        ),
    },
    "comments": {
        "type": "noul",
        "instructions": (
            "Does `comment` only restate what `next_lines` already say, adding no reason, "
            "constraint or consequence that a reader could not get from the code itself?"
        ),
    },
    "algorithm": {
        "type": "noul",
        "instructions": (
            "Inside a loop over the input, does `code` repeat a linear scan (`in` on a list, "
            "`.index`, `.remove`, a nested loop, filtering a list) where a set or dict built once "
            "would remove it? A loop over a small constant, or inherently pairwise work, does not count."
        ),
    },
}
WHY = {"scope": "may not serve the request", "comments": "may only restate the code",
       "algorithm": "may repeat a linear scan"}


def git(*args: str, ok_codes: tuple[int, ...] = (0,)) -> str:
    result = subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8",
                            errors="replace", check=False)
    if result.returncode not in ok_codes:
        raise SystemExit(f"jev gate: git {' '.join(args[:3])} failed: {result.stderr.strip()}")
    return result.stdout


def read_diff(root: str, base: str | None, paths: list[str]) -> str:
    # quotepath off keeps non-ASCII names unquoted, and fixed prefixes override a user's
    # diff.noprefix or diff.mnemonicPrefix, so `parse` can trust the "+++ b/" header.
    # -W widens each hunk to its whole function, the unit the algorithm gate was piloted on.
    flags = ("-c", "core.quotepath=off", "diff", "--no-color", "--no-ext-diff", "-W",
             "--src-prefix=a/", "--dst-prefix=b/")
    if base:
        against = ("--merge-base", base)
    elif git("rev-parse", "--verify", "-q", "HEAD", ok_codes=(0, 1)).strip():
        against = ("HEAD",)
    else:  # a repo with no commit yet: compare with the empty tree
        against = (git("hash-object", "-t", "tree", "/dev/null").strip(),)
    diff = git(*flags, *against, "--", *paths)
    untracked = git("ls-files", "--others", "--exclude-standard", "--full-name", "-z", "--", *paths)
    for path in filter(None, untracked.split("\0")):
        diff += git("-C", root, *flags, "--no-index", "--", "/dev/null", path, ok_codes=(0, 1))
    return diff


def parse(diff: str) -> list[dict]:
    """One {file, start, lines} per hunk; lines keep their diff marker."""
    hunks: list[dict] = []
    path, in_header = None, False
    for line in diff.split("\n"):
        if line.startswith("diff --git"):
            path, in_header = None, True
        elif in_header and line.startswith("+++ "):
            target = line[4:].strip()
            path = None if target == "/dev/null" else target.removeprefix("b/")
        elif line.startswith("@@") and path:
            in_header = False
            hunks.append({"file": path, "start": int(re.match(r"@@ -\S+ \+(\d+)", line).group(1)), "lines": []})
        elif path and not in_header and line[:1] in (" ", "+", "-"):
            hunks[-1]["lines"].append(line)
    return [hunk for hunk in hunks
            if Path(hunk["file"]).name not in LOCKFILES and not hunk["file"].endswith(GENERATED)]


def numbered(hunk: dict) -> list[tuple[int, str, str]]:
    rows, line_no = [], hunk["start"]
    for line in hunk["lines"]:
        rows.append((line_no, line[0], line[1:]))
        if line[0] != "-":
            line_no += 1
    return rows


def is_comment(text: str, prefixes: tuple[str, ...]) -> bool:
    text = text.strip()
    if not text.startswith(prefixes) or DIRECTIVE.match(text):
        return False
    # A bare * continues a block comment only before a space, a slash or nothing: `*p = 3` is code.
    return not text.startswith("*") or text == "*" or text[1] in " /"


def clip(lines: list[str], anchor: int) -> str:
    """At most _MAX_STATE_CHARS, starting a little above `anchor` so the change itself survives."""
    text = "\n".join(lines)
    if len(text) <= _MAX_STATE_CHARS:
        return text
    return "\n".join(lines[max(0, anchor - 20):])[:_MAX_STATE_CHARS]


def near_changes(rows: list[tuple[int, str, str]]) -> list[str]:
    """The changed rows with a few lines of context, as a plain unified hunk would show them."""
    changed = [i for i, row in enumerate(rows) if row[1] != " "]
    lines, previous = [], None
    for i, row in enumerate(rows):
        if not any(abs(i - c) <= _CONTEXT for c in changed):
            continue
        if previous is not None and i > previous + 1:
            lines.append("...")
        lines.append(row[1] + row[2])
        previous = i
    return lines


def items_for(hunks: list[dict], request: str | None) -> list[dict]:
    items = []
    for hunk in hunks:
        file, rows = hunk["file"], numbered(hunk)
        changed = [row for row in rows if row[1] != " "]
        if not changed:
            continue
        first = next((row for row in changed if row[1] == "+"), changed[0])
        line, label = first[0], first[2].strip()[:60]
        if request:
            items.append({"gate": "scope", "file": file, "line": line, "label": label,
                          "state": {"request": request, "file": file, "hunk": clip(near_changes(rows), 0)}})
        suffix = Path(file).suffix.lower()
        prefixes = COMMENT_PREFIXES.get(suffix)
        if not prefixes:
            continue
        i = 0
        while i < len(rows):
            if not (rows[i][1] == "+" and is_comment(rows[i][2], prefixes)):
                i += 1
                continue
            j = i
            while j < len(rows) and rows[j][1] == "+" and is_comment(rows[j][2], prefixes):
                j += 1
            comment = "\n".join(row[2] for row in rows[i:j])[:_MAX_COMMENT_CHARS]
            after = [row[2] for row in rows[j:] if row[1] != "-"][:4]
            items.append({"gate": "comments", "file": file, "line": rows[i][0],
                          "label": rows[i][2].strip()[:60],
                          "state": {"comment": comment, "next_lines": "\n".join(after)}})
            i = j
        if suffix in CONFIG_SUFFIXES or TEST_PATH.search(file):
            continue
        new_side = [row for row in rows if row[1] != "-"]
        # The loop may be an unchanged line: a scan added inside an existing loop is the classic case.
        has_loop = any(LOOP.search(row[2]) and not is_comment(row[2], prefixes) for row in new_side)
        if has_loop and any(row[1] == "+" for row in new_side):
            anchor = next(k for k, row in enumerate(new_side) if row[1] == "+")
            items.append({"gate": "algorithm", "file": file, "line": line, "label": label,
                          "state": {"code": clip([row[2] for row in new_side], anchor)}})
    return items


def risk(result: dict) -> float:
    return 1 - result["noul"] if result["gate"] == "scope" else result["noul"]


def report(results: list[dict], scope_checked: bool) -> str:
    done = [result for result in results if "noul" in result]
    leads = sorted((r for r in done if risk(r) >= _LEAD), key=risk, reverse=True)
    unsure = sorted((r for r in done if _UNSURE <= risk(r) < _LEAD), key=risk, reverse=True)
    counts = ", ".join(f"{n} {gate}" for gate, n in Counter(r["gate"] for r in results).items())
    models = ", ".join(sorted({r["model"] for r in done if r.get("model")})) or "?"
    tokens = sum(r.get("tokens", 0) for r in done)
    lines = [f"jev gate: checked {counts}; {len(leads)} lead(s), {len(unsure)} unsure "
             f"(risk 0 to 1, model {models}, {tokens} input tokens)"]
    for title, rows in (("Leads, check each before changing anything:", leads),
                        ("Unsure, judge these yourself:", unsure)):
        if rows:
            lines.append(title)
            lines += [f"  {r['gate']:<9} {risk(r):.2f}  {r['file']}:{r['line']}  {WHY[r['gate']]}: {r['label']}"
                      for r in rows]
    failed = [r for r in results if "error" in r]
    if failed:
        lines.append(f"{len(failed)} FAILED: " + "; ".join(f"{r['file']}:{r['line']} {r['error']}" for r in failed))
    if not scope_checked:
        lines.append("Scope not checked: pass --request with what was asked.")
    return "\n".join(lines)


def run(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="jev.py gate", description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="judge everything since the merge base with this ref")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--request", help="what was asked; enables the scope gate")
    source.add_argument("--request-file", type=Path)
    parser.add_argument("--out", type=Path, help="write every score as JSON")
    parser.add_argument("paths", nargs="*", help="limit the diff to these paths")
    args = parser.parse_args(argv)

    # The diff covers the whole repo whatever the cwd, so the root is what must be allowed.
    root = git("rev-parse", "--show-toplevel").strip()
    if not is_allowed(root, load_config()):
        print(f"jev gate: {root} is not in hooks_allow, and the gates send its code to "
              "TypeSafe. Add it with: jev.py allow FOLDER", file=sys.stderr)
        return 2
    request = (args.request or (args.request_file.read_text() if args.request_file else "")).strip() or None
    items = items_for(parse(read_diff(root, args.base, args.paths)), request)
    if not items:
        print("jev gate: nothing to check in this diff")
        return 0
    if len(items) > _MAX_ITEMS:
        print(f"jev gate: {len(items)} items is over {_MAX_ITEMS}; pass paths to narrow the diff",
              file=sys.stderr)
        return 2
    key = api_key()

    def judge(item: dict) -> dict:
        try:
            reply = ask(item["state"], {item["gate"]: QUESTIONS[item["gate"]]}, key=key)
            noul = float(reply["answers"][item["gate"]]["noul"])
        except JevAuthError:
            raise  # every other item would fail the same way
        except (JevError, KeyError, TypeError, ValueError) as error:
            return {**item, "error": str(error)[:200]}
        return {**item, "noul": noul, "model": reply.get("model"),
                "tokens": reply.get("usage", {}).get("input_tokens", 0)}

    with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
        results = list(pool.map(judge, items))
    print(report(results, scope_checked=request is not None))
    if args.out:
        rows = [{k: v for k, v in r.items() if k != "state"} for r in results]
        args.out.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    return 1 if any("error" in r for r in results) else 0
