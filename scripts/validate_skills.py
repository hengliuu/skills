#!/usr/bin/env python3
"""Validate every skills/*/*/SKILL.md and the plugin.json skills list. Needs PyYAML (pip install pyyaml)."""
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MAX_DESCRIPTION = 1024
MAX_LINES = 500
LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^\s*(```|~~~)")


def frontmatter(text):
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    data = yaml.safe_load(text[4:end])
    return data if isinstance(data, dict) else None


def links(text):
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            line = re.sub(r"`[^`]*`", "", line)
            yield from LINK.findall(line)


def check(skill_md):
    errors = []
    folder = skill_md.parent
    text = skill_md.read_text(encoding="utf-8")
    try:
        meta = frontmatter(text)
    except yaml.YAMLError as exc:
        return [f"frontmatter does not parse: {exc}"]
    if meta is None:
        return ["missing or malformed frontmatter (expected a --- block at the top)"]
    if meta.get("name") != folder.name:
        errors.append(f"name {meta.get('name')!r} does not equal directory {folder.name!r}")
    desc = meta.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errors.append("description is missing or empty")
    elif len(desc) > MAX_DESCRIPTION:
        errors.append(f"description is {len(desc)} chars, limit {MAX_DESCRIPTION}")
    lines = len(text.splitlines())
    if lines > MAX_LINES:
        errors.append(f"SKILL.md is {lines} lines, limit {MAX_LINES}")
    for target in links(text):
        if re.match(r"^([a-z][a-z0-9+.-]*:|#|/)", target, re.I):
            continue
        path = target.split("#", 1)[0]
        if not path:
            continue
        resolved = (folder / path).resolve()
        if folder.resolve() not in resolved.parents and resolved != folder.resolve():
            errors.append(f"link {target!r} leaves the skill folder")
        elif not resolved.exists():
            errors.append(f"link {target!r} does not resolve")
    return errors


def check_manifest(skills):
    """plugin.json must list exactly the skill directories that exist."""
    listed = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")).get("skills", [])
    errors = []
    for entry in listed:
        if not (ROOT / entry / "SKILL.md").is_file():
            errors.append(f"plugin.json lists {entry!r} but it has no SKILL.md")
    on_disk = {skill_md.parent.resolve() for skill_md in skills}
    for folder in sorted(on_disk - {(ROOT / entry).resolve() for entry in listed}):
        errors.append(f"{folder.relative_to(ROOT)} is not listed in plugin.json")
    return errors


def main():
    skills = sorted(ROOT.glob("skills/*/*/SKILL.md"))
    if not skills:
        print("validate_skills: no SKILL.md files found", file=sys.stderr)
        return 1
    failed = 0
    for skill_md in skills:
        rel = skill_md.relative_to(ROOT)
        for error in check(skill_md):
            print(f"FAIL {rel}: {error}", file=sys.stderr)
            failed += 1
    for error in check_manifest(skills):
        print(f"FAIL .claude-plugin/plugin.json: {error}", file=sys.stderr)
        failed += 1
    if failed:
        print(f"validate_skills: {failed} problem(s) in {len(skills)} skills", file=sys.stderr)
        return 1
    print(f"validate_skills: {len(skills)} skills OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
