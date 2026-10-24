"""Keep the Claude Code agent files in step with references/model-map.md.

The map travels with the skill through the skills CLI; the agent files stay in the
plugin. Outside the plugin tree (a skills-CLI install) there are no agent files and the
wrapper tests skip.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
MAP_PATH = SKILL_DIR / "references" / "model-map.md"
PLUGIN_ROOT = SKILL_DIR.parents[2]
SKILLS_ROOT = PLUGIN_ROOT / "skills"
AGENTS_DIR = PLUGIN_ROOT / "agents"
PLUGIN_NAME = "hengliuu-skills"

COLUMNS = ("model", "effort", "autoCompactWindow", "tools", "skills")
ABSENT = "—"
COMPACT_MIN, COMPACT_MAX = 100_000, 1_000_000


def claude_code_table(text: str) -> dict[str, dict[str, str]]:
    """Rows of the first table under '## Claude Code', keyed by role."""
    section = text.split("## Claude Code", 1)[1].split("\n## ", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("|")]
    header = [cell.strip(" `") for cell in rows[0].strip("|").split("|")]
    if header != ["Role", *COLUMNS]:
        raise AssertionError(f"unexpected model-map header: {header}")
    table = {}
    for line in rows[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        table[cells[0]] = dict(zip(COLUMNS, (normalise(c) for c in cells[1:])))
    return table


def normalise(cell: str) -> str:
    """'`a`, `b`' -> 'a, b'; '—' stays '—'."""
    return ", ".join(part.strip(" `") for part in cell.split(","))


def frontmatter(path: Path) -> dict[str, str]:
    """The flat 'key: value' frontmatter these files use; YAML flow lists are flattened."""
    text = path.read_text()
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise AssertionError(f"{path} has no frontmatter")
    fields = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            value = ", ".join(item.strip() for item in value[1:-1].split(","))
        fields[key.strip()] = value
    return fields


class ModelMapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.table = claude_code_table(MAP_PATH.read_text())
        self.agent_roles = {
            role: row for role, row in self.table.items() if role != "orchestrator"
        }

    def test_compact_windows_are_integers_in_range(self) -> None:
        for role, row in self.table.items():
            value = row["autoCompactWindow"]
            if value == ABSENT:
                continue
            with self.subTest(role=role):
                self.assertRegex(value, r"^\d+$", "an integer token count, not '300K'")
                self.assertGreaterEqual(int(value), COMPACT_MIN)
                self.assertLessEqual(int(value), COMPACT_MAX)

    def test_preloaded_skills_are_namespaced_and_exist(self) -> None:
        for role, row in self.agent_roles.items():
            for skill in row["skills"].split(", "):
                with self.subTest(role=role, skill=skill):
                    plugin, _, name = skill.partition(":")
                    self.assertEqual(plugin, PLUGIN_NAME, "a bare name can resolve to another skill")
                    candidates = sorted(SKILLS_ROOT.glob(f"*/{name}/SKILL.md"))
                    self.assertEqual(len(candidates), 1, f"expected one skill named {name}")
                    skill_md = candidates[0]
                    fields = frontmatter(skill_md)
                    self.assertEqual(fields.get("name"), name)
                    self.assertNotEqual(
                        fields.get("disable-model-invocation"), "true",
                        "a skill with disable-model-invocation cannot be preloaded",
                    )

    def test_fable_is_not_mapped(self) -> None:
        self.assertNotIn("fable", " ".join(str(row) for row in self.table.values()))


@unittest.skipUnless(AGENTS_DIR.is_dir(), "agent files ship only with the Claude Code plugin")
class AgentFileTests(unittest.TestCase):
    def setUp(self) -> None:
        table = claude_code_table(MAP_PATH.read_text())
        self.agent_roles = {
            role: row for role, row in table.items() if role != "orchestrator"
        }

    def test_one_agent_file_per_mapped_role(self) -> None:
        files = {path.stem for path in AGENTS_DIR.glob("*.md")}
        self.assertEqual(files, set(self.agent_roles))

    def test_agent_frontmatter_matches_map(self) -> None:
        for role, row in self.agent_roles.items():
            fields = frontmatter(AGENTS_DIR / f"{role}.md")
            with self.subTest(role=role):
                self.assertEqual(fields.get("name"), role)
                for column in COLUMNS:
                    expected = row[column]
                    actual = fields.get(column, ABSENT)
                    self.assertEqual(actual, expected, f"{role}.md {column}")


if __name__ == "__main__":
    unittest.main()
