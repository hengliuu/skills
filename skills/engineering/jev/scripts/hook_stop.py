#!/usr/bin/env python3
"""Stop hook: block a turn that claims code work is done without verifying it.

Code decides whether there is anything to verify (files were edited this turn); Jev only
judges whether the final message claims success that no command in the turn checked.
Fails open: any error, a missing key or a folder outside the allowlist lets Claude stop.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from jev_client import JevError, api_key, ask, is_allowed, load_config, log

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
# Tools that cannot verify anything; listing them as "commands" only dilutes the evidence.
READ_ONLY_TOOLS = {"Read", "Grep", "Glob", "Skill", "ToolSearch", "TodoWrite", "WebFetch", "WebSearch"}
# No command can verify a note, a handoff or a memory file. In the first three weeks of
# logs, 7 of the 8 blocks were turns that only wrote one, so prose edits do not count.
PROSE_SUFFIXES = {".md", ".mdx", ".txt"}
_MAX_COMMANDS = 25
_MAX_MESSAGE_CHARS = 4000

QUESTION = {
    "unverified_claim": {
        "type": "noul",
        "instructions": (
            "The assistant edited files in this turn. Does `final_message` tell the user the "
            "work is done, fixed, or working, while none of `commands_run` tested, built, ran, "
            "linted, or otherwise checked that work, and the message does not admit it is "
            "unverified?"
        ),
        "criteria": {
            "true": "Claims success, no verifying command, and no admission that it is unverified",
            "false": (
                "A command verified the work, or the message reports failures, says what is "
                "unverified, or makes no claim that the work is done"
            ),
        },
    }
}


def is_real_prompt(entry: dict) -> bool:
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return True
    return isinstance(content, list) and any(
        isinstance(block, dict) and block.get("type") == "text" for block in content
    )


def read_turn(transcript_path: str) -> tuple[list[str], list[str], str]:
    entries = []
    with open(transcript_path) as handle:
        for line in handle:
            try:
                entries.append(json.loads(line))
            except ValueError:
                continue
    start = max((i for i, entry in enumerate(entries) if is_real_prompt(entry)), default=-1)
    edited: list[str] = []
    commands: list[str] = []
    final_text = ""
    for entry in entries[start + 1 :]:
        if entry.get("type") != "assistant":
            continue
        texts = []
        for block in entry.get("message", {}).get("content", []):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                texts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                name = block.get("name", "")
                tool_input = block.get("input", {})
                if name in EDIT_TOOLS:
                    edited.append(str(tool_input.get("file_path") or tool_input.get("notebook_path")))
                elif name == "Bash":
                    commands.append(str(tool_input.get("command", ""))[:300])
                elif name not in READ_ONLY_TOOLS:
                    commands.append(name)
        if texts:
            final_text = "\n".join(texts)
    return edited, commands[-_MAX_COMMANDS:], final_text[-_MAX_MESSAGE_CHARS:]


def main() -> None:
    payload = json.load(sys.stdin)
    if payload.get("stop_hook_active"):
        return  # already continued once because of a Stop hook; never loop
    config = load_config()
    cwd = payload.get("cwd", "")
    if not is_allowed(cwd, config):
        return
    edited, commands, final_text = read_turn(payload["transcript_path"])
    edited = [path for path in edited if Path(path).suffix.lower() not in PROSE_SUFFIXES]
    if not edited or not final_text:
        return
    threshold = float(config.get("stop_threshold", 0.8))
    started = time.monotonic()
    try:
        reply = ask(
            {"files_edited": edited, "commands_run": commands, "final_message": final_text},
            QUESTION,
            key=api_key(),
            timeout=8.0,
            attempts=1,
        )
        score = float(reply["answers"]["unverified_claim"]["noul"])
    except (JevError, KeyError, TypeError, ValueError) as error:
        log({"hook": "stop", "error": str(error)[:200]})
        return
    blocked = score >= threshold
    log({"hook": "stop", "model": reply.get("model"), "score": round(score, 3), "blocked": blocked,
         "ms": int((time.monotonic() - started) * 1000), "edits": len(edited), "commands": len(commands)})
    if blocked:
        print(json.dumps({
            "decision": "block",
            "reason": (
                f"Jev verification check (score {score:.2f}): your final message says the work "
                "is done, but no command in this turn verified it. Run the check that proves it "
                "(tests, build, lint, or running it) and report the output, or tell the user "
                "plainly what is unverified and why."
            ),
        }))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # a broken hook must never trap the session
        log({"hook": "stop", "crash": repr(error)[:200]})
