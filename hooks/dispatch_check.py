#!/usr/bin/env python3
"""PreToolUse on Agent: two warnings when the main session dispatches a role or a project agent.

- model: the dispatch passes a `model` that differs from the agent file (which mirrors the
  role-orchestrator model map). Once per role per session. Never blocks, because some
  overrides can be deliberate.
- tier: workflow-map has not run in this session, so nobody picked the execution tier from
  the plan's task table. Once per session.

HENGLIUU_GATES=off silences both.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

PLUGIN = "hengliuu-skills"


def agent_file(subagent_type: str, cwd: str) -> Path | None:
    """The agent file behind a dispatch, or None when it is not a role or a project agent."""
    if subagent_type.startswith(f"{PLUGIN}:"):
        root = os.environ.get("CLAUDE_PLUGIN_ROOT") or str(Path(__file__).resolve().parents[1])
        path = Path(root) / "agents" / f"{subagent_type.split(':', 1)[1]}.md"
        return path if path.is_file() else None
    if not subagent_type or ":" in subagent_type:
        return None
    for folder in (Path(cwd), *Path(cwd).parents):
        path = folder / ".claude" / "agents" / f"{subagent_type}.md"
        if path.is_file():
            return path
    return None


def file_model(path: Path) -> str:
    match = re.search(r"^model:\s*(\S+)", path.read_text().split("\n---", 1)[0], re.M)
    return match.group(1) if match else ""


def skill_ran(transcript: str, skill: str) -> bool:
    try:
        lines = open(transcript, encoding="utf-8", errors="ignore")
    except (OSError, TypeError):
        return False
    with lines:
        for line in lines:
            if skill not in line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            content = (entry.get("message") or {}).get("content")
            if entry.get("type") == "user" and isinstance(content, str):
                if re.search(rf"<command-name>/?(?:[\w-]+:)?{skill}</command-name>", content):
                    return True
            elif entry.get("type") == "assistant" and isinstance(content, list):
                for block in content:
                    if (isinstance(block, dict) and block.get("type") == "tool_use"
                            and block.get("name") == "Skill"
                            and str((block.get("input") or {}).get("skill", "")).split(":")[-1] == skill):
                        return True
    return False


def first_time(session: str, key: str) -> bool:
    marker = Path(tempfile.gettempdir()) / "hengliuu-skills-gates" / re.sub(r"[^\w.-]", "_", f"{session}.{key}")
    if marker.exists():
        return False
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()
    except OSError:
        return False
    return True


def main() -> None:
    if os.environ.get("HENGLIUU_GATES", "").lower() in ("off", "0", "false"):
        return
    payload = json.load(sys.stdin)
    if payload.get("agent_id"):
        return
    args = payload.get("tool_input") or {}
    role = str(args.get("subagent_type", ""))
    path = agent_file(role, str(payload.get("cwd", "")))
    if path is None:
        return
    session, notes = str(payload.get("session_id", "")), []

    expected, passed = file_model(path), str(args.get("model") or "")
    if passed and expected and passed != expected and first_time(session, f"model.{role}"):
        notes.append(
            f"Model check: the role-orchestrator model map sets `{expected}` for `{role}`, and this "
            f"dispatch passes `{passed}`. A deliberate override carries its reason in the reply. "
            "A dispatch without `model` runs on the agent file's value.")
    if first_time(session, "tier") and not skill_ran(payload.get("transcript_path", ""), "workflow-map"):
        notes.append(
            "Tier check: workflow-map has not run in this session. It is the skill that reads an "
            "approved plan's task table and picks the execution tier.")
    if notes:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "additionalContext": "\n\n".join(notes)}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:  # a broken check must never block a dispatch
        pass
