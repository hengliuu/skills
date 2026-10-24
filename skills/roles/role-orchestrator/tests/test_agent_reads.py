"""agent_reads.py against a session folder laid out the way Claude Code writes one."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "agent_reads.py"


def use(use_id: str, tool: str, **inputs: object) -> dict:
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": use_id, "name": tool, "input": inputs}]}}


def result(use_id: str, content: object, is_error: bool = False) -> dict:
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": use_id, "content": content, "is_error": is_error}]}}


class AgentReadsReport(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.session = Path(self.tmp.name) / "s1"
        agents = self.session / "subagents"
        agents.mkdir(parents=True)
        (agents / "agent-a1.meta.json").write_text(json.dumps(
            {"description": "K1 kit baseline", "agentType": "hengliuu-skills:worker"}))
        entries = [
            use("1", "Bash", command="cd /w && cat src/fields.tsx"), result("1", "x" * 900),
            use("2", "Bash", command="cd /w && graft skeleton src/form.tsx"), result("2", "y" * 100),
            use("3", "Read", file_path="/w/README.md"), result("3", "z" * 1000),
            use("4", "Read", file_path="/w/shot.png"),
            result("4", [{"type": "image", "source": {"data": "A" * 50_000}}]),
            use("5", "Read", file_path="/w/src/big.ts"),
            result("5", "PreToolUse:Read hook error: Code map first (hengliuu-skills gate): src/big.ts", True),
            use("7", "Read", file_path="/w/notes.md"), result("7", "- **Code map first:** run graft"),
            use("8", "Bash", command="sed -i '' 's/a/b/' src/fields.tsx"), result("8", ""),
            use("6", "Agent", name="helper", subagent_type="hengliuu-skills:designer", prompt="p"),
            result("6", "spawned"),
        ]
        (agents / "agent-a1.jsonl").write_text("".join(json.dumps(entry) + "\n" for entry in entries))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def report(self) -> dict:
        out = subprocess.run([sys.executable, str(SCRIPT), str(self.session), "--json"],
                             capture_output=True, text=True, check=True).stdout
        return json.loads(out.splitlines()[0])

    def test_counts_per_agent(self) -> None:
        row = self.report()
        self.assertEqual((row["agent"], row["role"]), ("K1 kit baseline", "hengliuu-skills:worker"))
        self.assertEqual((row["calls"], row["graft_calls"], row["source_reads"]), (8, 1, 2))
        denial = len("PreToolUse:Read hook error: Code map first (hengliuu-skills gate): src/big.ts")
        self.assertEqual((row["source_chars"], row["graft_chars"]), (900 + denial, 100))
        self.assertEqual((row["gate_denials"], row["named_spawns"]), (1, 1))

    def test_images_do_not_count_as_output(self) -> None:
        denial = len("PreToolUse:Read hook error: Code map first (hengliuu-skills gate): src/big.ts")
        notes = len("- **Code map first:** run graft")
        self.assertEqual(self.report()["output_chars"], 900 + 100 + 1000 + denial + notes + len("spawned"))

    def test_main_transcript_path_finds_the_session(self) -> None:
        main = self.session.with_suffix(".jsonl")
        main.write_text("")
        out = subprocess.run([sys.executable, str(SCRIPT), str(main)],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn("K1 kit baseline", out)


if __name__ == "__main__":
    unittest.main()
