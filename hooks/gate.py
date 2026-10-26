#!/usr/bin/env python3
"""PreToolUse gate for two Golden Rules the model skips under load.

- karpathy: the first code-file write of a session (Edit, Write, NotebookEdit, or a
  Bash command that writes a code file) is denied once unless karpathy-guidelines was invoked.
- review: the first `git merge` / `git cherry-pick` of a work branch is denied once unless a
  reviewer agent or requesting-code-review ran in the session.

Each gate fires at most once per session, so a retry always passes: it is a stop to think,
never a loop. Subagents are skipped (their agent files preload karpathy, and they do not
merge), with one exception: a subagent's Agent call with a `name` is always denied, because
with agent teams on it spawns a teammate at several times the cost, and dropping the name is
the way through. HENGLIUU_GATES=off disables all three.
"""

import json
import os
import re
import sys
import tempfile
from pathlib import Path

CODE_EXT = (
    "py|pyi|go|rs|ts|tsx|js|jsx|mjs|cjs|java|kt|kts|swift|rb|php|c|h|cc|cpp|hpp|cs|scala|dart|"
    "lua|ex|exs|sh|bash|zsh|sql|vue|svelte|tf|ipynb|yml|yaml|toml"
)
CODE_FILE = re.compile(rf"\.(?:{CODE_EXT})$|(?:^|/)(?:Dockerfile|Makefile|Justfile)$", re.I)
_CODE_PATH = rf"[\w./~-]+\.(?:{CODE_EXT})\b"
# Shell writes an Edit hook would never see: redirects, tee, in-place sed/perl, patches, and
# interpreter scripts (heredoc or -c/-e) that call a write API on a path naming a code file.
BASH_WRITE = [
    re.compile(rf"(?:>>?|\btee\s+(?:-a\s+)?)\s*[\"']?{_CODE_PATH}"),
    re.compile(rf"\b(?:g?sed|perl)\b[^|;&\n]*\s-\w*i.*{_CODE_PATH}", re.S),  # -i, -pi, -0pi, -i.bak
    re.compile(r"\bgit\s+apply\b|\bpatch\s+-p\d"),
]
_INTERPRETER = re.compile(r"\b(?:python3?|node|ruby|perl|deno|bun)\b[^\n|;]*(?:<<|\s-[ce]\s)")
_WRITE_API = re.compile(r"write_text|write_bytes|\.write\(|open\([^)]*['\"][wa]|writeFileSync|writeFile\(|File\.write")
_MERGE = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?(merge|cherry-pick)\b([^;&|\n]*)")
_BASE_REF = re.compile(r"^(?:origin|upstream)/|^(?:main|master|develop|HEAD)$")
REVIEWER_AGENT = re.compile(r"(?:^|:)(?:reviewer|code-reviewer)$")


def bash_writes_code(command: str) -> bool:
    if any(pattern.search(command) for pattern in BASH_WRITE):
        return True
    return bool(_INTERPRETER.search(command) and _WRITE_API.search(command)
                and re.search(_CODE_PATH, command))


def merges_work_branch(command: str) -> bool:
    """A merge or cherry-pick that brings a work branch in, not one that syncs from the base."""
    for match in _MERGE.finditer(command):
        args = match.group(2).split()
        if any(arg in ("--abort", "--continue", "--quit", "--skip") for arg in args):
            continue
        refs = [arg for arg in args if not arg.startswith("-")]
        if not refs or not all(_BASE_REF.search(ref) for ref in refs):
            return True
    return False


def transcript_calls(path: str, needle: str) -> list[dict]:
    """Inputs of the assistant's tool calls on lines that mention `needle`, plus slash commands."""
    calls: list[dict] = []
    try:
        handle = open(path, encoding="utf-8", errors="ignore")
    except (OSError, TypeError):
        return calls
    with handle:
        for line in handle:
            if needle not in line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            content = (entry.get("message") or {}).get("content")
            if entry.get("type") == "user" and isinstance(content, str):
                for name in re.findall(r"<command-name>/?([^<]+)</command-name>", content):
                    calls.append({"tool": "Skill", "skill": name})
            elif entry.get("type") == "assistant" and isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        calls.append({"tool": block.get("name"), **(block.get("input") or {})})
    return calls


def skill_ran(path: str, skill: str) -> bool:
    return any(call["tool"] == "Skill" and str(call.get("skill", "")).split(":")[-1] == skill
               for call in transcript_calls(path, skill))


def review_ran(path: str) -> bool:
    if skill_ran(path, "requesting-code-review"):
        return True
    return any(call["tool"] in ("Agent", "Task")
               and REVIEWER_AGENT.search(str(call.get("subagent_type", "")))
               for call in transcript_calls(path, "reviewer"))


def should_block(session: str, gate: str, satisfied) -> bool:
    """Decide a gate once per session: the first trigger records it, later ones pass unchecked."""
    safe_session = re.sub(r"[^\w-]", "_", session)  # a backslash inside an f-string breaks Python 3.9
    marker = Path(tempfile.gettempdir()) / "hengliuu-skills-gates" / f"{safe_session}.{gate}"
    if marker.exists():
        return False
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        return False  # no state means no way to stay one-shot, so never block
    return not satisfied()


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason,
    }}))


def main() -> None:
    if os.environ.get("HENGLIUU_GATES", "").lower() in ("off", "0", "false"):
        return
    payload = json.load(sys.stdin)
    tool, args = payload.get("tool_name"), payload.get("tool_input") or {}
    if payload.get("agent_id"):
        if tool == "Agent" and args.get("name"):
            deny("Dispatched agents spawn without a `name` (hengliuu-skills gate): with agent teams on, "
                 "a named spawn becomes a teammate at several times the cost. Drop `name` and "
                 "retry. If your brief needs a team, stop and say so in your report instead.")
        return
    session, transcript = str(payload.get("session_id", "")), payload.get("transcript_path", "")
    command = str(args.get("command", "")) if tool == "Bash" else ""

    path = str(args.get("file_path") or args.get("notebook_path") or "")
    if (CODE_FILE.search(path) if tool != "Bash" else bash_writes_code(command)) \
            and should_block(session, "karpathy", lambda: skill_ran(transcript, "karpathy-guidelines")):
        deny("Golden Rule: invoke karpathy-guidelines before writing code (hengliuu-skills gate, "
             "once per session). Invoke it with the Skill tool, then retry. If this edit is "
             "trivial, say so and retry: the gate will not fire again this session.")
        return

    if tool == "Bash" and merges_work_branch(command) \
            and should_block(session, "review", lambda: review_ran(transcript)):
        deny("Golden Rule: no reviewer ran in this session before this merge (hengliuu-skills gate, "
             "once per session). Dispatch a reviewer on the range (without subagents, invoke "
             "requesting-code-review), then merge. If review already happened elsewhere, say "
             "where and retry: the gate will not fire again this session.")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a broken gate must never block work
        pass
