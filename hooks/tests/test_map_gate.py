"""Run map_gate.py the way Claude Code does: a PreToolUse payload on stdin, a decision on stdout."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "map_gate.py"
sys.path.insert(0, str(GATE.parent))
import map_gate  # noqa: E402


def tool_use(use_id: str, name: str, **inputs: object) -> dict:
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": use_id, "name": name, "input": inputs}]}}


def tool_result(use_id: str, text: str) -> dict:
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": use_id, "content": text}]}}


class MapGate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        (self.repo / "graft").mkdir(parents=True)
        (self.repo / "graft" / "INDEX.md").write_text("# map\n")
        (self.repo / "src").mkdir()
        self.big = self.repo / "src" / "big.ts"
        self.big.write_text("const value = 1; // padding\n" * 400)
        self.other = self.repo / "src" / "other.ts"
        self.other.write_text("const value = 1; // padding\n" * 400)
        (self.repo / "small.ts").write_text("export {}\n")
        self.main_transcript = root / "session.jsonl"
        self.main_transcript.write_text("")
        self.transcript = root / "session" / "subagents" / "agent-a1.jsonl"
        self.transcript.parent.mkdir(parents=True)
        self.transcript.write_text("")
        self.bin = root / "bin"
        self.bin.mkdir()
        graft = self.bin / "graft"
        graft.write_text("#!/bin/sh\n")
        graft.chmod(graft.stat().st_mode | stat.S_IXUSR)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def log(self, *entries: dict) -> None:
        with self.transcript.open("a") as handle:
            handle.writelines(json.dumps(entry) + "\n" for entry in entries)

    def run_raw(self, stdin: str, env: dict | None = None) -> subprocess.CompletedProcess:
        run_env = {**os.environ, "TMPDIR": self.tmp.name, "PATH": f"{self.bin}:{os.environ['PATH']}",
                   **(env or {})}
        return subprocess.run([sys.executable, str(GATE)], input=stdin, capture_output=True,
                              text=True, env=run_env)

    def run_gate(self, tool: str, env: dict | None = None, agent: str | None = "a1",
                 cwd: Path | None = None, **tool_input: object) -> dict | None:
        payload = {"session_id": "s", "cwd": str(cwd or self.repo), "tool_name": tool,
                   "tool_input": tool_input, "transcript_path": str(self.main_transcript)}
        if agent:
            payload["agent_id"] = agent
        result = self.run_raw(json.dumps(payload), env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else None

    def read(self, path: Path, **kwargs: object) -> dict | None:
        return self.run_gate("Read", file_path=str(path), **kwargs)

    def assertDenied(self, decision: dict | None) -> str:
        self.assertIsNotNone(decision)
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")
        return decision["hookSpecificOutput"]["permissionDecisionReason"]

    def test_whole_read_denied_with_the_command_for_that_file(self) -> None:
        reason = self.assertDenied(self.read(self.big))
        self.assertIn(f"graft skeleton src/big.ts {self.repo}`", reason)

    def test_denial_repeats_per_file_until_graft_names_it(self) -> None:
        self.assertDenied(self.read(self.big))
        self.assertDenied(self.read(self.big))
        self.log(tool_use("g1", "Bash", command="cd /x/repo && graft skeleton src/big.ts"),
                 tool_result("g1", "graft skeleton — src/big.ts\n- L1-L4  function value"))
        self.assertIsNone(self.read(self.big))

    def test_graft_naming_one_file_leaves_the_other_gated(self) -> None:
        self.log(tool_use("g1", "Bash", command='graft ask "where is value" --source'),
                 tool_result("g1", "1. value · const\n   src/big.ts:L1-L1"))
        self.assertIsNone(self.read(self.big))
        self.assertDenied(self.read(self.other))

    def test_graft_mcp_answer_names_the_file(self) -> None:
        self.log(tool_use("m1", "mcp__graft__graft_find_code", query="value"),
                 tool_result("m1", [{"type": "text", "text": "1. value\nsrc/big.ts:L1-L1\n"}]))
        self.assertIsNone(self.read(self.big))

    def test_graft_repo_map_does_not_name_files(self) -> None:
        self.log(tool_use("m1", "mcp__graft__graft_repo_map"), tool_result("m1", "hotspots: src/big.ts"),
                 tool_use("g1", "Bash", command="graft map"), tool_result("g1", "src/big.ts"))
        self.assertDenied(self.read(self.big))

    def test_same_suffix_in_another_package_is_not_named(self) -> None:
        nested = self.repo / "packages" / "b" / "src" / "big.ts"
        nested.parent.mkdir(parents=True)
        nested.write_text(self.big.read_text())
        self.log(tool_use("g1", "Bash", command='graft ask "value"'), tool_result("g1", "src/big.ts:L1-L1"))
        self.assertIsNone(self.read(self.big))
        self.assertDenied(self.read(nested))

    def test_route_folder_path_is_matched(self) -> None:
        page = self.repo / "app" / "(app)" / "temuan" / "[id]" / "page.tsx"
        page.parent.mkdir(parents=True)
        page.write_text(self.big.read_text())
        self.log(tool_use("g1", "Bash", command='graft ask "temuan"'),
                 tool_result("g1", "1. Page (app/(app)/temuan/[id]/page.tsx:L1-L9)"))
        self.assertIsNone(self.read(page))

    def test_gitignored_file_passes(self) -> None:
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True)
        (self.repo / ".gitignore").write_text("dist/\n")
        built = self.repo / "dist" / "bundle.js"
        built.parent.mkdir()
        built.write_text(self.big.read_text())
        self.assertIsNone(self.read(built))

    def test_skeleton_run_from_the_files_folder_names_it(self) -> None:
        self.log(tool_use("g1", "Bash", command="graft skeleton big.ts"), tool_result("g1", "no definitions"))
        self.assertIsNone(self.run_gate("Read", cwd=self.big.parent, file_path=str(self.big)))

    def test_skeleton_with_root_argument_names_the_file(self) -> None:
        self.log(tool_use("g1", "Bash", command=f"graft skeleton src/big.ts {self.repo}"),
                 tool_result("g1", "no wiring graph"))
        self.assertIsNone(self.run_gate("Read", cwd=Path("/"), file_path=str(self.big)))

    def test_mentioning_graft_is_not_running_it(self) -> None:
        self.log(tool_use("g1", "Bash", command='grep -n "graft skeleton src/big.ts" README.md'))
        self.assertDenied(self.read(self.big))

    def test_gives_up_after_max_denies(self) -> None:
        for _ in range(map_gate.MAX_DENIES):
            self.assertDenied(self.read(self.big))
        self.assertIsNone(self.read(self.big))

    def test_paging_with_narrow_ranges_is_counted(self) -> None:
        self.assertIsNone(self.run_gate("Bash", command="sed -n '1,60p' src/big.ts"))
        self.assertIsNone(self.read(self.big, offset=61, limit=50))
        self.assertDenied(self.run_gate("Bash", command="sed -n '111,140p' src/big.ts"))

    def test_denied_read_is_not_counted(self) -> None:
        self.assertDenied(self.run_gate("Bash", command="cat src/big.ts src/other.ts"))
        self.assertIsNone(self.read(self.other, offset=1, limit=100))

    def test_small_file_and_non_source_pass(self) -> None:
        self.assertIsNone(self.read(self.repo / "small.ts"))
        for name in ("notes.md", "values.yaml", "deploy.sh", "data.json", "schema.sql"):
            (self.repo / name).write_text("line of text, long enough\n" * 500)
            self.assertIsNone(self.read(self.repo / name))

    def test_each_agent_is_gated_separately(self) -> None:
        self.assertDenied(self.read(self.big, agent="a1"))
        self.assertDenied(self.read(self.big, agent="a2"))

    def test_main_session_is_skipped(self) -> None:
        self.assertIsNone(self.read(self.big, agent=None))

    def test_worktree_finds_the_main_checkout_index(self) -> None:
        git = ["git", "-C", str(self.repo)]
        subprocess.run([*git, "init", "-q"], check=True)
        subprocess.run([*git, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q",
                        "--allow-empty", "-m", "init"], check=True)
        worktree = Path(self.tmp.name) / "wt"
        subprocess.run([*git, "worktree", "add", "-q", str(worktree)], check=True)
        (worktree / "big.ts").write_text(self.big.read_text())
        self.assertFalse((worktree / "graft").exists())
        self.assertDenied(self.run_gate("Read", cwd=worktree, file_path=str(worktree / "big.ts")))

    def test_no_index_is_silent(self) -> None:
        (self.repo / "graft" / "INDEX.md").unlink()
        self.assertIsNone(self.read(self.big))

    def test_graft_not_installed_is_silent(self) -> None:
        (self.bin / "graft").unlink()
        path = os.pathsep.join(p for p in os.environ["PATH"].split(os.pathsep)
                               if not (Path(p) / "graft").exists() and not (Path(p) / "trail").exists())
        self.assertIsNone(self.read(self.big, env={"PATH": path}))

    def test_env_switch_disables(self) -> None:
        self.assertIsNone(self.read(self.big, env={"HENGLIUU_GATES": "off"}))

    def test_malformed_input_never_blocks(self) -> None:
        for stdin in ("", "not json", "[]", '{"agent_id": "a", "tool_input": "x"}'):
            with self.subTest(stdin=stdin):
                result = self.run_raw(stdin)
                self.assertEqual((result.returncode, result.stdout), (0, ""))


class BashReads(unittest.TestCase):
    def lines(self, command: str, total: int = 400) -> list[int]:
        return [map_gate.span_lines(span, total) for _, span in map_gate.bash_reads(command, "/r")]

    def test_whole_file_dumpers(self) -> None:
        for command in ("cat a.ts", "nl a.ts", "less a.ts", "bat a.ts", "cat a.ts 2>&1", "sed 's/x/y/' a.ts",
                        "cat a.ts 2>/dev/null", "cat < a.ts", "cat > s.sh <<'EOF'\ncat x.ts\nEOF\ncat a.ts",
                        "cat <<-EOF > s.sh\n\tcat x.ts\n\tEOF\ncat a.ts", "cat a.ts >&2"):
            with self.subTest(command=command):
                self.assertEqual(self.lines(command), [400])

    def test_counted_spans(self) -> None:
        cases = {"head a.ts": [10], "head -n 50 a.ts": [50], "head --lines=300 a.ts": [300],
                 "head -n -5 a.ts": [395], "tail -20 a.ts": [20], "tail -n +5 a.ts": [396],
                 "sed -n '10,60p' a.ts": [51], "sed -n '1,20p;300,$p' a.ts": [20, 101],
                 "sed -n 7p a.ts": [1], "bat -r 1:20 a.ts": [20], "tail -n 0 a.ts": [0],
                 "cat a.ts | head -n 50": [50], "cat -n a.ts | head -300": [300],
                 "nl -ba a.ts | sed -n '1,300p'": [300], "git show HEAD:a.ts | sed -n 1,200p": [200]}
        for command, expected in cases.items():
            with self.subTest(command=command):
                self.assertEqual(self.lines(command), expected)

    def test_not_a_read_into_context(self) -> None:
        for command in ("head -c 100 a.ts", "grep -n value a.ts", "x=$(cat a.ts)", "cat a.ts >& out.log",
                        "cat a.ts|grep value", "sed -i.bak 's/a/b/' a.ts", "sed -Ei 's/a/b/' a.ts",
                        "cat a.ts | grep x | head -300", "cat a.ts > b.ts", "cat <<EOF > a.ts", "sed -i '' 's/a/b/' a.ts",
                        "sed -n '/re/p' a.ts", "python3 - <<'EOF'\ns=open('a.ts').read()\nEOF",
                        "cat > s.sh <<'EOF'\ncat a.ts\nEOF", "cat a.ts &> out.log"):
            with self.subTest(command=command):
                self.assertEqual(self.lines(command), [])

    def test_commands_after_a_heredoc_are_all_read(self) -> None:
        command = "cat > s.sh <<'EOF'\nbody\nEOF\ncat a.ts\ncat b.ts"
        self.assertEqual([path for path, _ in map_gate.bash_reads(command, "/r")], ["/r/a.ts", "/r/b.ts"])

    def test_paths_resolve(self) -> None:
        self.assertEqual(map_gate.bash_reads("cat 'sp ace.ts'", "/r"), [("/r/sp ace.ts", map_gate.WHOLE)])
        self.assertEqual(map_gate.bash_reads("cd /w && cat a.ts", "/r"), [("/w/a.ts", map_gate.WHOLE)])
        self.assertEqual(map_gate.bash_reads("git show HEAD:src/a.ts", "/not-a-repo"),
                         [("/not-a-repo/src/a.ts", map_gate.WHOLE)])


if __name__ == "__main__":
    unittest.main()
