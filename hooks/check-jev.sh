#!/usr/bin/env bash
# jev SessionStart: will Jev's hooks fire in this folder, and can they reach Jev?
#
# The router and the unverified-done check fall back to a static reminder and fail open
# when Jev is unusable, so a dead key, a network fault, or a folder outside `hooks_allow`
# all look exactly like a healthy session. This says which one it is. It stays silent
# when there is no config at all (Jev was never set up, so every install without a TypeSafe
# key would be nagged) and when the folder is outside a non-empty `hooks_allow` (a choice,
# for client folders): nothing there will call Jev, and it must not nag every session.
#
# The key lookup and the request are jev_client's, so this check agrees with the hooks it
# reports on. The probe sends one synthetic question about `n`, never repo content, and
# only runs in folders where the hooks are allowed to run.

set -uo pipefail

ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
SCRIPTS="$ROOT/skills/engineering/jev/scripts"
TIMEOUT=6
# `python3` is missing, or a Microsoft Store stub, on Windows; `python` is the name there.
PY=python3
python3 -c '' >/dev/null 2>&1 || PY=python

warn() { printf '\n⚠️  jev: %s\n' "$1"; }

# --- is this folder under a hooks_allow root? ---------------------------------------
# jev_client's own check, so a malformed entry means the same thing here as in the hooks.
allow_state=$(PYTHONPATH="$SCRIPTS" "$PY" - "$PWD" <<'PY' 2>/dev/null
import sys

from jev_client import CONFIG_PATH, is_allowed, load_config

if not CONFIG_PATH.exists():
    print("unset")
    raise SystemExit
config = load_config()
if not config["hooks_allow"]:
    print("noconfig")
else:
    print("allowed" if is_allowed(sys.argv[1], config) else "outside")
PY
)

case "$allow_state" in
  allowed) ;;
  unset | outside) exit 0 ;;
  noconfig)
    warn "no folder is allowlisted, so Jev's hooks are off everywhere."
    printf 'They send the prompt or the final message to a cloud API, so they only run in\n'
    printf 'folders you name. The guided setup stores the key and asks which folders to allow;\n'
    printf 'allow only folders that hold no client data:\n'
    printf '  %s %s/jev.py setup\n' "$PY" "$SCRIPTS"
    exit 0
    ;;
  *)
    warn "Jev's status could not be determined (python3 or python is required)."
    exit 0
    ;;
esac

# --- can the hooks reach Jev with the stored key? ------------------------------------
probe=$(PYTHONPATH="$SCRIPTS" "$PY" - "$TIMEOUT" <<'PY' 2>/dev/null
import sys

from jev_client import JevAuthError, JevError, ask, find_key

try:
    _, key = find_key()
except JevError:
    print("nokey")
    raise SystemExit
try:
    ask({"n": 7}, {"q": {"type": "noul", "instructions": "Is `n` equal to 7?"}},
        key=key, timeout=float(sys.argv[1]), attempts=1)
except JevAuthError:
    print("auth")
except JevError:
    print("unreachable")
else:
    print("ok")
PY
)

case "${probe:-unknown}" in
  ok) exit 0 ;;
  nokey)
    warn "Jev has no API key, so its hooks are silently inert here."
    printf 'Store it once, in a terminal (nothing you type is shown):\n\n'
    printf '  %s %s/jev.py key\n' "$PY" "$SCRIPTS"
    ;;
  auth)
    warn "Jev rejected the stored API key (401)."
    printf 'A stale key fails every hook call the same way; replace it, in a terminal:\n\n'
    printf '  %s %s/jev.py key\n' "$PY" "$SCRIPTS"
    printf '\nA TYPESAFE_API_KEY exported in your shell overrides the stored key: unset it if the\n'
    printf 'stored key is the right one.\n'
    ;;
  unreachable)
    warn "Jev is configured but could not answer."
    printf 'Its hooks fail open, so this session runs without the judgment layer. Retry\n'
    printf 'later with: %s %s/jev.py --check\n' "$PY" "$SCRIPTS"
    ;;
  *)
    warn "Jev's status could not be determined."
    printf 'Check it with: %s %s/jev.py --check\n' "$PY" "$SCRIPTS"
    ;;
esac

printf '\nUntil Jev is usable, judge the calls it would have made yourself. The jev skill\n'
printf 'covers when a call is worth making; it says to decide alone when Jev is down.\n'

exit 0
