"""Run gate.py the way Claude Code does: a PreToolUse payload on stdin, a decision on stdout."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "gate.py"
sys.path.insert(0, str(GATE.parent))
import gate  # noqa: E402


def tool_use(name: str, **inputs) -> str:
    return json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t", "name": name, "input": inputs}]}})


class GateRun(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.transcript = Path(self.tmp.name) / "t.jsonl"
        self.transcript.write_text("")
        self.session = 0

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def new_session(self) -> None:
        self.session += 1

    def run_gate(self, tool: str, env: dict | None = None, **tool_input) -> dict | None:
        payload = {"session_id": f"s{self.session}", "transcript_path": str(self.transcript),
                   "tool_name": tool, "tool_input": tool_input, **tool_input.pop("_extra", {})}
        result = subprocess.run(
            [sys.executable, str(GATE)], input=json.dumps(payload), capture_output=True, text=True,
            env={**os.environ, "TMPDIR": self.tmp.name, **(env or {})}, check=True)
        return json.loads(result.stdout) if result.stdout.strip() else None

    def assertDenied(self, decision: dict | None) -> None:
        self.assertIsNotNone(decision)
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_code_edit_denied_once_then_passes(self) -> None:
        self.assertDenied(self.run_gate("Edit", file_path="/r/app/main.go"))
        self.assertIsNone(self.run_gate("Edit", file_path="/r/app/main.go"))

    def test_docs_edit_passes(self) -> None:
        self.assertIsNone(self.run_gate("Write", file_path="/r/README.md"))
        self.assertIsNone(self.run_gate("Edit", file_path="/r/manifest.json"))

    def test_invoked_skill_passes(self) -> None:
        self.transcript.write_text(tool_use("Skill", skill="hengliuu-skills:karpathy-guidelines") + "\n")
        self.assertIsNone(self.run_gate("Write", file_path="/r/a.py"))

    def test_slash_command_counts_as_invoked(self) -> None:
        line = {"type": "user", "message": {"content":
                "<command-name>/hengliuu-skills:karpathy-guidelines</command-name>"}}
        self.transcript.write_text(json.dumps(line) + "\n")
        self.assertIsNone(self.run_gate("Write", file_path="/r/a.ts"))

    def test_router_mention_is_not_an_invoke(self) -> None:
        line = {"type": "user", "message": {"content": [
            {"type": "text", "text": "Skill router: hengliuu-skills:karpathy-guidelines (0.9)"}]}}
        self.transcript.write_text(json.dumps(line) + "\n")
        self.assertDenied(self.run_gate("Write", file_path="/r/a.rs"))

    def test_bash_heredoc_write_is_caught(self) -> None:
        self.assertDenied(self.run_gate("Bash", command=(
            "python3 - <<'EOF'\nfrom pathlib import Path\nPath('svc/handler.go').write_text(x)\nEOF")))

    def test_bash_sed_in_place_is_caught(self) -> None:
        self.assertDenied(self.run_gate("Bash", command="sed -i '' 's/a/b/' src/app.ts"))

    def test_bash_bundled_in_place_flags_are_caught(self) -> None:
        for command in ("perl -0pi -e 's/a/b/' billing/invoice.ts", "sed -i.bak 's/a/b/' x.go",
                        "cat >> billing/invoice.ts <<'EOF'\nexport const a = 1\nEOF"):
            with self.subTest(command=command):
                self.new_session()
                self.assertDenied(self.run_gate("Bash", command=command))

    def test_bash_redirect_is_caught(self) -> None:
        self.assertDenied(self.run_gate("Bash", command="cat > lefthook.yml <<'EOF'\npre-commit:\nEOF"))

    def test_bash_reads_pass(self) -> None:
        for command in ("cat src/app.ts", "grep -n x a.py > /tmp/out.txt", "go test ./...",
                        "python3 -c 'print(1)'", "sed -n 1,20p main.go"):
            with self.subTest(command=command):
                self.new_session()
                self.assertIsNone(self.run_gate("Bash", command=command))

    def test_subagent_is_skipped(self) -> None:
        self.assertIsNone(self.run_gate("Edit", file_path="/r/a.go", _extra={"agent_id": "a1"}))

    def test_subagent_named_spawn_is_always_denied(self) -> None:
        spawn = {"subagent_type": "hengliuu-skills:designer", "prompt": "p", "_extra": {"agent_id": "a1"}}
        self.assertDenied(self.run_gate("Agent", name="audit-a", **dict(spawn)))
        self.assertDenied(self.run_gate("Agent", name="audit-a", **dict(spawn)))
        self.assertIsNone(self.run_gate("Agent", **dict(spawn)))

    def test_main_session_named_spawn_passes(self) -> None:
        self.assertIsNone(self.run_gate("Agent", name="lead", subagent_type="x", prompt="p"))

    def test_env_switch_disables(self) -> None:
        self.assertIsNone(self.run_gate("Edit", env={"HENGLIUU_GATES": "off"}, file_path="/r/a.go"))

    def test_merge_without_review_denied_once(self) -> None:
        self.transcript.write_text(tool_use("Skill", skill="karpathy-guidelines") + "\n")
        self.assertDenied(self.run_gate("Bash", command="git merge --ff-only task/42-login"))
        self.assertIsNone(self.run_gate("Bash", command="git merge --ff-only task/43-logout"))

    def test_merge_after_reviewer_passes(self) -> None:
        self.transcript.write_text(tool_use("Agent", subagent_type="hengliuu-skills:reviewer",
                                            prompt="review", description="r") + "\n")
        self.assertIsNone(self.run_gate("Bash", command="git cherry-pick abc123"))

    def test_syncing_from_base_is_not_a_merge_of_work(self) -> None:
        for command in ("git merge origin/main", "git merge --abort", "git cherry-pick --continue"):
            with self.subTest(command=command):
                self.new_session()
                self.assertIsNone(self.run_gate("Bash", command=command))


class Patterns(unittest.TestCase):
    def test_code_file(self) -> None:
        for path in ("a.go", "x/Dockerfile", "ci.yaml", "nb.ipynb"):
            self.assertTrue(gate.CODE_FILE.search(path), path)
        for path in ("README.md", "plugin.json", "notes.txt"):
            self.assertFalse(gate.CODE_FILE.search(path), path)


if __name__ == "__main__":
    unittest.main()
