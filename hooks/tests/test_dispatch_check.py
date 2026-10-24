"""Run dispatch_check.py with a PreToolUse Agent payload and read the context it adds."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parents[1]
CHECK = HOOKS / "dispatch_check.py"


class DispatchCheck(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.transcript = self.root / "t.jsonl"
        self.transcript.write_text("")
        (self.root / "repo" / ".claude" / "agents").mkdir(parents=True)
        (self.root / "repo" / ".claude" / "agents" / "backend.md").write_text(
            "---\nname: backend\nmodel: sonnet\n---\nbody\n")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_check(self, env: dict | None = None, **tool_input) -> str:
        payload = {"session_id": "s1", "transcript_path": str(self.transcript),
                   "cwd": str(self.root / "repo" / "sub"), "tool_name": "Agent",
                   "tool_input": {"prompt": "p", "description": "d", **tool_input}}
        result = subprocess.run(
            [sys.executable, str(CHECK)], input=json.dumps(payload), capture_output=True, text=True,
            env={**os.environ, "TMPDIR": self.tmp.name, "CLAUDE_PLUGIN_ROOT": str(HOOKS.parent),
                 **(env or {})}, check=True)
        if not result.stdout.strip():
            return ""
        return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]

    def test_model_override_warns_once_per_role(self) -> None:
        first = self.run_check(subagent_type="hengliuu-skills:worker", model="opus")
        self.assertIn("sets `sonnet`", first)
        self.assertEqual(self.run_check(subagent_type="hengliuu-skills:worker", model="opus"), "")

    def test_matching_or_absent_model_is_silent_after_tier_note(self) -> None:
        self.assertIn("Tier check", self.run_check(subagent_type="hengliuu-skills:chore"))
        self.assertEqual(self.run_check(subagent_type="hengliuu-skills:chore", model="haiku"), "")

    def test_project_agent_found_from_a_subfolder(self) -> None:
        self.assertIn("sets `sonnet`", self.run_check(subagent_type="backend", model="opus"))

    def test_workflow_map_run_silences_tier(self) -> None:
        self.transcript.write_text(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "hengliuu-skills:workflow-map"}}]}}) + "\n")
        self.assertEqual(self.run_check(subagent_type="hengliuu-skills:worker"), "")

    def test_other_agents_and_switch_are_silent(self) -> None:
        self.assertEqual(self.run_check(subagent_type="Explore", model="haiku"), "")
        self.assertEqual(self.run_check(env={"HENGLIUU_GATES": "off"},
                                        subagent_type="hengliuu-skills:worker", model="opus"), "")


if __name__ == "__main__":
    unittest.main()
