"""Shared TypeSafe Jev client for the jev skill and the Jev hooks (stdlib only)."""

from __future__ import annotations

import http.client
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-latest"
CONFIG_PATH = Path.home() / ".claude" / "jev" / "config.json"
DEFAULTS_PATH = Path(__file__).resolve().parent.parent / "config.default.json"
KEY_PATH = Path.home() / ".claude" / "jev" / "key"
JEV_CLI = Path(__file__).resolve().with_name("jev.py")
_NO_KEY = "no TYPESAFE_API_KEY in the environment, the key file or the Keychain"
LOG_PATH = Path.home() / ".claude" / "jev" / "hooks.log.jsonl"
_RETRY_STATUSES = {429, 529}
_ATTEMPTS = 3



class JevError(Exception):
    pass


class JevAuthError(JevError):
    """The key was rejected; retrying cannot help until the user stores a new one."""


def find_key() -> tuple[str, str]:
    """(source, key) from the environment, then the key file, then the macOS Keychain."""
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if key:
        return "environment", key
    # Hooks do not inherit a login shell, so a stored key beats relying on an exported variable.
    try:
        key = KEY_PATH.read_text().strip()
    except OSError:
        key = ""
    if key:
        return "key file", key
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "TYPESAFE_API_KEY", "-w"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
    except (OSError, subprocess.TimeoutExpired) as error:  # no `security` outside macOS, or a locked keychain
        raise JevError(_NO_KEY) from error
    key = result.stdout.strip()
    if result.returncode != 0 or not key:
        raise JevError(_NO_KEY)
    return "Keychain", key


def api_key() -> str:
    return find_key()[1]


def ask(
    state: object,
    questions: dict[str, object],
    *,
    key: str,
    timeout: float = 20.0,
    attempts: int = _ATTEMPTS,
    model: str | None = None,
) -> dict:
    """`attempts` × `timeout` must fit a hook's own timeout, or the hook is killed silently."""
    body = json.dumps({"state": state, "model": model or configured_model(), "questions": questions}).encode()
    request = urllib.request.Request(
        JEV_URL,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            if error.code in _RETRY_STATUSES and attempt < attempts - 1:
                time.sleep(0.5 * 2**attempt)
                continue
            detail = error.read().decode(errors="replace")[:300]
            if error.code in (401, 403):
                raise JevAuthError(f"TypeSafe rejected the key ({error.code})") from error
            raise JevError(f"TypeSafe returned {error.code}: {detail}") from error
        except (OSError, http.client.HTTPException) as error:  # URLError is an OSError, and so is a read timeout on 3.9
            raise JevError(f"could not reach TypeSafe: {error}") from error
        except ValueError as error:
            raise JevError(f"TypeSafe sent a reply that is not JSON: {error}") from error
    raise JevError("TypeSafe stayed rate limited")


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_config() -> dict:
    """The plugin's defaults under the user's own config.

    `hooks_allow` never comes from the defaults: it opts a folder into sending text to a
    cloud API, so only the user's file may grow it. A `router_skills` entry set to null
    drops a default skill.
    """
    defaults, own = _read_json(DEFAULTS_PATH), _read_json(CONFIG_PATH)
    config = {**defaults, **own}
    config["hooks_allow"] = own.get("hooks_allow", [])
    skills = {**defaults.get("router_skills", {}), **own.get("router_skills", {})}
    config["router_skills"] = {name: text for name, text in skills.items() if text}
    return config


def configured_model() -> str:
    """`model` in config.json pins a version or tries `jev-preview`; unset follows `jev-latest`."""
    return str(load_config().get("model") or JEV_MODEL)


def allowed_root(entry: object) -> Path | None:
    """An allowlist entry that may open a folder: absolute, and not everything below `~` or `/`.

    A hand-edited config can hold a bare string or "." or "/", and any of those would
    otherwise open every folder to a cloud API, so an entry that cannot be trusted opens none.
    """
    if not isinstance(entry, str):
        return None
    root = Path(entry).expanduser()
    if not root.is_absolute():
        return None
    root = root.resolve()
    return None if root in (Path.home().resolve(), Path(root.anchor)) else root


def is_allowed(cwd: str, config: dict) -> bool:
    """Hooks send session text to a cloud API, so only opted-in folders may use them."""
    entries = config.get("hooks_allow", [])
    if not isinstance(entries, list):
        return False
    here = Path(cwd).expanduser().resolve()
    for entry in entries:
        root = allowed_root(entry)
        if root is not None and (here == root or root in here.parents):
            return True
    return False


def log(event: dict) -> None:
    """Metadata only (never prompt or message text), for measuring false alarms and latency."""
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a") as handle:
            handle.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **event}) + "\n")
    except OSError:
        pass
