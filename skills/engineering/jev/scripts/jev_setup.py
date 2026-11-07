"""Guided setup and allowlist edits for the Jev hooks (stdlib only).

    jev.py setup             store the key if none is found, allow folders, then test the key
    jev.py key               store a new key (replaces a stale one), then test it
    jev.py allow FOLDER      add a folder to hooks_allow
    jev.py allowed           list the folders in hooks_allow
"""

from __future__ import annotations

import getpass
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import jev_client
from jev_client import JevError

COMMANDS = ("setup", "key", "allow", "allowed")

_PRIVACY = (
    "The hooks send your prompt to TypeSafe, and after a turn that edited files, the file names,\n"
    "the commands and the final message. Allow only folders that hold no client data."
)


class ConfigError(Exception):
    """The config cannot be edited safely; the message says what to fix."""


def _load_own() -> dict[str, object]:
    """The user's file exactly as written. It is never rewritten when it does not parse."""
    path = jev_client.CONFIG_PATH
    if not path.exists():
        return {}
    try:
        data: object = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise ConfigError(f"{path} is not valid JSON; fix it by hand first") from error
    if not isinstance(data, dict):
        raise ConfigError(f"{path} must hold a JSON object; fix it by hand first")
    return data


def _save(config: dict[str, object]) -> None:
    path = jev_client.CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_suffix(".tmp")
    staged.write_text(json.dumps(config, indent=2) + "\n")
    staged.replace(path)


def _roots(config: dict[str, object]) -> list[str]:
    roots = config.get("hooks_allow", [])
    if not isinstance(roots, list):
        raise ConfigError(f"hooks_allow in {jev_client.CONFIG_PATH} must be a list")
    return [str(root) for root in roots]


def _stored_form(folder: Path) -> str:
    """`~/x` under the home folder, so the entry means the same on every machine."""
    home = Path.home().resolve()
    if home in folder.parents:
        return "~/" + folder.relative_to(home).as_posix()
    return folder.as_posix()


def allow(folder: str) -> str:
    path = Path(folder).expanduser().resolve()
    if not path.is_dir():
        raise ConfigError(f"{path} is not a folder")
    if path in (Path.home().resolve(), Path(path.anchor)):
        raise ConfigError(f"{path} is too broad: name the projects you mean, not everything")
    config = _load_own()
    roots = _roots(config)
    for root in roots:
        resolved = Path(root).expanduser().resolve()
        if path == resolved or resolved in path.parents:
            return f"already allowed: {path} (covered by {root})"
    stored = _stored_form(path)
    config["hooks_allow"] = [*roots, stored]
    _save(config)
    return f"allowed: {stored}"


def allowed() -> list[str]:
    return _roots(_load_own())


def _write_key_file(key: str) -> None:
    path = jev_client.KEY_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        handle.write(key + "\n")
    path.chmod(0o600)  # an existing file keeps its old mode otherwise


def store_key(read_secret: Callable[[str], str] = getpass.getpass) -> None:
    if sys.platform == "darwin" and shutil.which("security"):
        print("macOS asks for the key twice and shows nothing you type.")
        subprocess.run(
            ["security", "add-generic-password", "-U", "-a", getpass.getuser(), "-s", "TYPESAFE_API_KEY", "-w"],
            check=False,
        )
        return
    key = read_secret("TypeSafe API key (nothing is shown): ").strip()
    if not key:
        print("No key entered.")
        return
    _write_key_file(key)
    print(f"Key stored in {jev_client.KEY_PATH}. It is plain text: keep the file private.")


def _key_step(read_secret: Callable[[str], str]) -> None:
    try:
        source, _ = jev_client.find_key()
    except JevError:
        print("Key: not stored yet.")
        store_key(read_secret)
    else:
        print(f"Key: found ({source}).")


def setup(read_line: Callable[[str], str] = input, read_secret: Callable[[str], str] = getpass.getpass) -> None:
    _key_step(read_secret)
    print(f"\n{_PRIVACY}")
    print(f"Allowed now: {', '.join(allowed()) or 'nothing'}")
    while folder := read_line("Folder to allow (blank to finish): ").strip():
        try:
            print(allow(folder))
        except ConfigError as error:
            print(error)


def run(command: str, args: list[str], *, check: Callable[[], int]) -> int:
    try:
        if command == "setup":
            setup()
            return check()
        if command == "key":
            store_key()
            return check()
        if command == "allow":
            if len(args) != 1:
                print("usage: jev.py allow FOLDER", file=sys.stderr)
                return 2
            print(allow(args[0]))
        else:
            print("\n".join(allowed()) or "(no folder is allowed)")
    except ConfigError as error:
        print(error, file=sys.stderr)
        return 1
    return 0
