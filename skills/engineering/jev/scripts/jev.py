#!/usr/bin/env python3
"""Ask Jev typed questions about one state or many items.

Usage: jev.py REQUEST.json [--out RESULT.json]
       jev.py --check    (is the stored key accepted? one tiny synthetic request)
       jev.py setup | key | allow FOLDER | allowed    (guided setup; see jev_setup.py)
       jev.py gate [--base REF] [--request TEXT] [PATH ...]    (diff quality gates; see jev_gate.py)
       jev.py route PLAN.md    (second pick of role and effort per task; see jev_route.py)

REQUEST.json holds "questions" (raw TypeSafe question objects) and either "state" (one
request) or "items": [{"id": ..., "state": ...}] (one request per item, run in parallel).
An optional "context" object is merged into every item's state as {"context", "item"}.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import jev_gate
import jev_route
import jev_setup
from jev_client import JEV_CLI, JevAuthError, JevError, api_key, ask, find_key

_WORKERS = 8
_CHECK_QUESTION = {"colour": {"type": "noul", "instructions": "Is `text` about a colour?"}}


def check() -> int:
    source, key = find_key()
    started = time.monotonic()
    try:
        reply = ask({"text": "The sky is blue."}, _CHECK_QUESTION, key=key, timeout=10.0)
    except JevAuthError as error:
        print(f"jev: FAIL, {error}; key from the {source}.", file=sys.stderr)
        if source == "environment":
            print("Fix or unset TYPESAFE_API_KEY in your shell; it overrides a stored key.", file=sys.stderr)
        else:
            print(f"Store a fresh key in a terminal: python3 {JEV_CLI} key", file=sys.stderr)
        return 1
    ms = int((time.monotonic() - started) * 1000)
    noul = reply["answers"]["colour"]["noul"]
    print(f"jev: OK, key from the {source}, model {reply.get('model', '?')}, {ms} ms, test answer {noul:.2f}")
    return 0


def main() -> int:
    if sys.argv[1:2] and sys.argv[1] in jev_setup.COMMANDS:
        return jev_setup.run(sys.argv[1], sys.argv[2:], check=check)
    if sys.argv[1:2] == ["gate"]:
        return jev_gate.run(sys.argv[2:])
    if sys.argv[1:2] == ["route"]:
        return jev_route.run(sys.argv[2:])
    parser = argparse.ArgumentParser()
    parser.add_argument("request", type=Path, nargs="?")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", action="store_true", help="test the stored key and exit")
    args = parser.parse_args()
    if args.check:
        return check()
    if args.request is None:
        parser.error("a request file is required unless --check is given")

    spec = json.loads(args.request.read_text())
    questions = spec["questions"]
    key = api_key()

    if "items" in spec:
        context = spec.get("context")
        items = spec["items"]

        def run(item: dict) -> tuple[str, dict]:
            state = item["state"] if context is None else {"context": context, "item": item["state"]}
            try:
                return str(item["id"]), ask(state, questions, key=key)
            except JevAuthError:
                raise  # every other item would fail the same way
            except JevError as error:
                # one bad item must not throw away the answers the others already paid for
                return str(item["id"]), {"error": str(error)}

        with ThreadPoolExecutor(max_workers=_WORKERS) as pool:
            replies = dict(pool.map(run, items))
    else:
        replies = {"_": ask(spec["state"], questions, key=key)}

    answers = {
        item_id: reply["answers"] if "answers" in reply else {"error": reply["error"]}
        for item_id, reply in replies.items()
    }
    failed = sum("error" in reply for reply in replies.values())
    tokens = sum(reply.get("usage", {}).get("input_tokens", 0) for reply in replies.values())
    models = sorted({reply["model"] for reply in replies.values() if "model" in reply})
    result = answers["_"] if list(answers) == ["_"] else answers

    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.write_text(text)
    else:
        print(text)
    summary = f"jev: {len(replies)} request(s), {tokens} input tokens, model {', '.join(models) or '?'}"
    if failed:
        summary += f"; {failed} FAILED (see their \"error\" field)"
    print(summary, file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except JevError as error:
        print(f"jev: {error}", file=sys.stderr)
        sys.exit(1)
