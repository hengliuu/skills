#!/usr/bin/env python3
"""UserPromptSubmit hook: name the skills this prompt calls for, judged by Jev.

The menu of skills is config.default.json overlaid by ~/.claude/jev/config.json ("router_skills"). One Noul per
skill runs in a single parallel request. Outside the allowlist, with no key, or when Jev
fails, the hook adds nothing: the prompt goes through unchanged, and the session-start check
says why Jev is not answering.
"""

from __future__ import annotations

import json
import sys
import time

from jev_client import (
    JEV_CLI,
    LOG_PATH,
    JevAuthError,
    JevError,
    api_key,
    ask,
    is_allowed,
    load_config,
    log,
)

_MAX_PROMPT_CHARS = 4000
_MIN_PROMPT_CHARS = 12
_AUTH_WARNED_PATH = LOG_PATH.with_name("auth_warned_session")


def auth_warning_once(session_id: str) -> str:
    """A rejected key otherwise fails silently in every hook; say so once per session."""
    try:
        if _AUTH_WARNED_PATH.read_text() == session_id:
            return ""
    except OSError:
        pass
    try:
        _AUTH_WARNED_PATH.write_text(session_id)
    except OSError:
        pass
    return (
        "Jev hooks are off: TypeSafe rejected the stored key (401). Tell the user once, and "
        f"that they can replace it in a terminal with `python3 {JEV_CLI} key`."
    )


def emit(text: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}
    }))


def questions_for(skills: dict[str, str]) -> dict[str, object]:
    return {
        name: {
            "type": "noul",
            "instructions": {
                "skill": {"name": name, "use_when": use_when},
                "question": (
                    "Should the assistant invoke `skill` before responding to `prompt`? "
                    "Answer yes only when the prompt's own task matches `skill.use_when`."
                ),
            },
        }
        for name, use_when in skills.items()
    }


def main() -> None:
    payload = json.load(sys.stdin)
    config = load_config()
    prompt = str(payload.get("prompt", "")).strip()
    skills: dict[str, str] = config.get("router_skills", {})
    if not skills or not is_allowed(payload.get("cwd", ""), config):
        return
    if len(prompt) < _MIN_PROMPT_CHARS or prompt.startswith("/"):
        return  # slash commands already name their skill; "ok"/"lanjut" need no routing
    threshold = float(config.get("router_threshold", 0.7))
    started = time.monotonic()
    try:
        reply = ask(
            {"prompt": prompt[:_MAX_PROMPT_CHARS]},
            questions_for(skills),
            key=api_key(),
            timeout=6.0,
            attempts=1,
        )
        scores = {name: float(reply["answers"][name]["noul"]) for name in skills}
    except JevAuthError as error:
        log({"hook": "router", "error": str(error)[:200]})
        warning = auth_warning_once(str(payload.get("session_id", "")))
        if warning:
            emit(warning)
        return
    except (JevError, KeyError, TypeError, ValueError) as error:
        log({"hook": "router", "error": str(error)[:200]})
        return
    picked = sorted(
        ((name, score) for name, score in scores.items() if score >= threshold),
        key=lambda pair: pair[1],
        reverse=True,
    )
    log({"hook": "router", "model": reply.get("model"), "ms": int((time.monotonic() - started) * 1000),
         "picked": {name: round(score, 2) for name, score in picked}})
    if picked:
        lines = [f"- {name} ({score:.2f}): {skills[name]}" for name, score in picked]
        emit(
            "Skill router (Jev, a filter not a judge): this prompt likely calls for\n"
            + "\n".join(lines)
            + "\nInvoke the ones that truly apply with the Skill tool before acting; ignore a "
            "false match."
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # a broken hook must never block the prompt
        log({"hook": "router", "crash": repr(error)[:200]})
