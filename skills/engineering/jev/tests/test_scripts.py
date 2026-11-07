"""Offline tests for the jev scripts: every Jev call is faked, nothing touches the network.

Run: python3 -m unittest discover -s tests   (from the skill folder)
"""

from __future__ import annotations

import http.client
import io
import json
import os
import re
import socket
import stat
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import hook_router  # noqa: E402
import hook_stop  # noqa: E402
import jev  # noqa: E402
import jev_client  # noqa: E402
import jev_gate  # noqa: E402
import jev_route  # noqa: E402
import jev_setup  # noqa: E402
from jev_client import JevAuthError, JevError  # noqa: E402

ALLOWED = "/tmp/jev-tests-allowed"
CONFIG = {
    "hooks_allow": [ALLOWED],
    "router_threshold": 0.7,
    "stop_threshold": 0.8,
    "router_skills": {"alpha": "The prompt asks for alpha.", "beta": "The prompt asks for beta."},
}


def noul_reply(**scores: float) -> dict:
    return {"answers": {name: {"noul": score} for name, score in scores.items()}, "model": "jev-test"}


def run_hook(module, payload: dict) -> str:
    out = io.StringIO()
    with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), redirect_stdout(out):
        module.main()
    return out.getvalue()


class JevCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(tempfile.mkdtemp())
        self.request = self.dir / "request.json"
        self.request.write_text(json.dumps({
            "items": [{"id": "good", "state": {"x": 1}}, {"id": "bad", "state": {"x": 2}}],
            "questions": {"q": {"type": "noul", "instructions": "?"}},
        }))
        patcher = mock.patch.object(jev, "api_key", return_value="k")
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(sys, "argv", ["jev.py", *argv]), redirect_stdout(out), redirect_stderr(err):
            code = jev.main()
        return code, out.getvalue(), err.getvalue()

    def test_one_failed_item_keeps_the_other_answers(self) -> None:
        def fake_ask(state, questions, *, key, **_):
            if state["x"] == 2:
                raise JevError("TypeSafe returned 422: bad state")
            return noul_reply(q=0.9)

        with mock.patch.object(jev, "ask", side_effect=fake_ask):
            code, out, err = self.run_cli(str(self.request))
        result = json.loads(out)
        self.assertEqual(result["good"], {"q": {"noul": 0.9}})
        self.assertIn("422", result["bad"]["error"])
        self.assertEqual(code, 1)
        self.assertIn("1 FAILED", err)

    def test_rejected_key_aborts_the_whole_run(self) -> None:
        with mock.patch.object(jev, "ask", side_effect=JevAuthError("rejected")):
            with self.assertRaises(JevAuthError):
                self.run_cli(str(self.request))

    def test_check_reports_ok_and_fail(self) -> None:
        with mock.patch.object(jev, "find_key", return_value=("Keychain", "k")):
            with mock.patch.object(jev, "ask", return_value=noul_reply(colour=0.97)):
                code, out, _ = self.run_cli("--check")
            self.assertEqual(code, 0)
            self.assertIn("key from the Keychain", out)
            with mock.patch.object(jev, "ask", side_effect=JevAuthError("TypeSafe rejected the key (401)")):
                code, _, err = self.run_cli("--check")
        self.assertEqual(code, 1)
        self.assertIn("jev.py key", err)


class ClientRetryTest(unittest.TestCase):
    def rate_limited(self, *_args, **_kwargs):
        raise urllib.error.HTTPError("u", 429, "busy", {}, io.BytesIO(b""))

    def test_hooks_get_a_single_attempt(self) -> None:
        with mock.patch.object(jev_client.urllib.request, "urlopen", side_effect=self.rate_limited) as urlopen:
            with self.assertRaises(JevError):
                jev_client.ask({}, {}, key="k", attempts=1)
        self.assertEqual(urlopen.call_count, 1)

    def test_401_is_an_auth_error(self) -> None:
        def unauthorised(*_args, **_kwargs):
            raise urllib.error.HTTPError("u", 401, "no", {}, io.BytesIO(b"{}"))

        with mock.patch.object(jev_client.urllib.request, "urlopen", side_effect=unauthorised):
            with self.assertRaises(JevAuthError):
                jev_client.ask({}, {}, key="k")

    def test_a_network_fault_is_a_jev_error_whatever_the_python_version(self) -> None:
        faults = [
            socket.timeout("read timed out"),  # not a TimeoutError before Python 3.10
            ConnectionResetError("reset"),
            http.client.RemoteDisconnected("closed"),
        ]
        for fault in faults:
            with mock.patch.object(jev_client.urllib.request, "urlopen", side_effect=fault):
                with self.assertRaises(JevError, msg=repr(fault)):
                    jev_client.ask({}, {}, key="k", attempts=1)

    def test_a_reply_that_is_not_json_is_a_jev_error(self) -> None:
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b"<html>gateway error</html>"
        with mock.patch.object(jev_client.urllib.request, "urlopen", return_value=response):
            with self.assertRaises(JevError):
                jev_client.ask({}, {}, key="k", attempts=1)


    def test_the_configured_model_is_sent_and_jev_latest_is_the_default(self) -> None:
        def sent_model(config: dict) -> str:
            response = mock.MagicMock()
            response.__enter__.return_value.read.return_value = b"{}"
            with mock.patch.object(jev_client, "load_config", return_value=config), \
                    mock.patch.object(jev_client.urllib.request, "urlopen", return_value=response) as urlopen:
                jev_client.ask({}, {}, key="k")
            return json.loads(urlopen.call_args.args[0].data)["model"]

        self.assertEqual(sent_model({"model": "jev-preview"}), "jev-preview")
        self.assertEqual(sent_model({}), "jev-latest")


class RouterHookTest(unittest.TestCase):
    def setUp(self) -> None:
        warned = Path(tempfile.mkdtemp()) / "auth_warned_session"
        for target, value in [
            ("load_config", mock.Mock(return_value=CONFIG)),
            ("api_key", mock.Mock(return_value="k")),
            ("log", mock.Mock()),
            ("_AUTH_WARNED_PATH", warned),
        ]:
            patcher = mock.patch.object(hook_router, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def payload(self, cwd: str = ALLOWED, session: str = "s1") -> dict:
        return {"prompt": "please do alpha for me", "cwd": cwd, "session_id": session}

    def test_picks_only_skills_above_the_threshold(self) -> None:
        with mock.patch.object(hook_router, "ask", return_value=noul_reply(alpha=0.9, beta=0.2)) as ask:
            out = run_hook(hook_router, self.payload())
        text = json.loads(out)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("alpha (0.90)", text)
        self.assertNotIn("beta", text)
        self.assertEqual(ask.call_args.kwargs["attempts"], 1)

    def test_outside_the_allowlist_never_calls_jev(self) -> None:
        with mock.patch.object(hook_router, "ask") as ask:
            out = run_hook(hook_router, self.payload(cwd="/somewhere/else"))
        ask.assert_not_called()
        self.assertEqual(out, "")

    def test_a_jev_failure_leaves_the_prompt_unchanged(self) -> None:
        with mock.patch.object(hook_router, "ask", side_effect=JevError("down")):
            self.assertEqual(run_hook(hook_router, self.payload()), "")

    def test_rejected_key_warns_once_per_session(self) -> None:
        with mock.patch.object(hook_router, "ask", side_effect=JevAuthError("rejected")):
            first = run_hook(hook_router, self.payload(session="s1"))
            second = run_hook(hook_router, self.payload(session="s1"))
            other = run_hook(hook_router, self.payload(session="s2"))
        self.assertIn("rejected the stored key", first)
        self.assertEqual(second, "")
        self.assertIn("rejected the stored key", other)


class StopHookTest(unittest.TestCase):
    def setUp(self) -> None:
        for target, value in [
            ("load_config", mock.Mock(return_value=CONFIG)),
            ("api_key", mock.Mock(return_value="k")),
            ("log", mock.Mock()),
        ]:
            patcher = mock.patch.object(hook_stop, target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.transcript = Path(tempfile.mkdtemp()) / "t.jsonl"
        entries = [
            {"type": "user", "message": {"content": "fix the bug"}},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Read", "input": {"file_path": "a.py"}},
                {"type": "tool_use", "name": "Edit", "input": {"file_path": "a.py"}},
                {"type": "tool_use", "name": "Agent", "input": {"prompt": "run tests"}},
                {"type": "tool_use", "name": "Bash", "input": {"command": "pytest -q"}},
            ]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Fixed, tests pass."}]}},
        ]
        self.transcript.write_text("\n".join(json.dumps(entry) for entry in entries))

    def test_read_only_tools_are_not_listed_as_commands(self) -> None:
        edited, commands, final = hook_stop.read_turn(str(self.transcript))
        self.assertEqual(edited, ["a.py"])
        self.assertEqual(commands, ["Agent", "pytest -q"])
        self.assertEqual(final, "Fixed, tests pass.")

    def test_blocks_above_threshold_and_never_loops(self) -> None:
        payload = {"cwd": ALLOWED, "transcript_path": str(self.transcript)}
        with mock.patch.object(hook_stop, "ask", return_value=noul_reply(unverified_claim=0.95)):
            self.assertEqual(json.loads(run_hook(hook_stop, payload))["decision"], "block")
            self.assertEqual(run_hook(hook_stop, {**payload, "stop_hook_active": True}), "")
        with mock.patch.object(hook_stop, "ask", return_value=noul_reply(unverified_claim=0.3)):
            self.assertEqual(run_hook(hook_stop, payload), "")


    def test_outside_the_allowlist_reads_nothing_and_sends_nothing(self) -> None:
        payload = {"cwd": "/somewhere/else", "transcript_path": str(self.transcript)}
        with mock.patch.object(hook_stop, "ask") as ask, \
                mock.patch.object(hook_stop, "read_turn") as read_turn:
            self.assertEqual(run_hook(hook_stop, payload), "")
        ask.assert_not_called()
        read_turn.assert_not_called()

    def test_a_turn_that_only_edited_prose_is_not_checked(self) -> None:
        entries = [
            {"type": "user", "message": {"content": "note the decision"}},
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Edit", "input": {"file_path": "/vault/human-gate.md"}},
                {"type": "tool_use", "name": "Write", "input": {"file_path": "notes.TXT"}},
                {"type": "text", "text": "Done, it is in the checklist."},
            ]}},
        ]
        self.transcript.write_text("\n".join(json.dumps(entry) for entry in entries))
        payload = {"cwd": ALLOWED, "transcript_path": str(self.transcript)}
        with mock.patch.object(hook_stop, "ask") as ask:
            self.assertEqual(run_hook(hook_stop, payload), "")
        ask.assert_not_called()


GATE_DIFF = """diff --git a/app.py b/app.py
index 1..2 100644
--- a/app.py
+++ b/app.py
@@ -10,3 +10,6 @@ def dedupe(rows):
     out = []
+    # loop over rows
+    # and keep new ones
     for row in rows:
-        out.append(row)
+        if row not in out:
+            out.append(row)
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1 +1 @@
-old
+# new heading
diff --git a/package-lock.json b/package-lock.json
--- a/package-lock.json
+++ b/package-lock.json
@@ -1 +1 @@
-{}
+{"a": 1}
diff --git a/gone.py b/gone.py
--- a/gone.py
+++ /dev/null
@@ -1 +0,0 @@
-x = 1
"""


class GateTest(unittest.TestCase):
    def test_items_cover_each_gate_and_skip_lockfiles_deletions_and_prose_comments(self) -> None:
        items = jev_gate.items_for(jev_gate.parse(GATE_DIFF), request="dedupe rows")
        found = {(item["gate"], item["file"], item["line"]) for item in items}
        self.assertEqual(found, {
            ("scope", "app.py", 11), ("comments", "app.py", 11), ("algorithm", "app.py", 11),
            ("scope", "README.md", 1),
        })
        comment = next(item for item in items if item["gate"] == "comments")
        self.assertEqual(comment["state"]["comment"], "    # loop over rows\n    # and keep new ones")
        self.assertEqual(comment["state"]["next_lines"].splitlines()[0].strip(), "for row in rows:")
        algorithm = next(item for item in items if item["gate"] == "algorithm")
        self.assertNotIn("out.append(row)\n        if", algorithm["state"]["code"])  # removed lines dropped

    def test_test_files_get_no_algorithm_check(self) -> None:
        for path in ("tests/test_app.py", "src/app.test.ts", "pkg/app_test.go", "web/__tests__/a.tsx"):
            hunks = jev_gate.parse(GATE_DIFF.replace("app.py", path))
            self.assertNotIn("algorithm", {item["gate"] for item in jev_gate.items_for(hunks, None)}, path)
        self.assertTrue(jev_gate.TEST_PATH.search("tests/x.py"))
        self.assertFalse(jev_gate.TEST_PATH.search("src/contest.py"))

    def test_without_a_request_scope_is_skipped(self) -> None:
        gates = {item["gate"] for item in jev_gate.items_for(jev_gate.parse(GATE_DIFF), request=None)}
        self.assertEqual(gates, {"comments", "algorithm"})

    def test_report_lists_leads_and_unsure_by_risk(self) -> None:
        base = {"file": "app.py", "line": 1, "label": "x", "model": "jev-test"}
        results = [
            {**base, "gate": "scope", "noul": 0.1},       # risk 0.9: a lead
            {**base, "gate": "comments", "noul": 0.5},    # unsure
            {**base, "gate": "algorithm", "noul": 0.2},   # passes, not listed
            {**base, "gate": "comments", "error": "503"},
        ]
        text = jev_gate.report(results, scope_checked=True)
        self.assertIn("1 lead(s), 1 unsure", text)
        self.assertIn("scope     0.90  app.py:1", text)
        self.assertNotIn("algorithm 0.20", text)
        self.assertIn("1 FAILED", text)

    def test_refuses_outside_the_allowlist_before_reading_the_diff(self) -> None:
        with mock.patch.object(jev_gate, "load_config", return_value=CONFIG), \
                mock.patch.object(jev_gate, "read_diff") as read_diff, redirect_stderr(io.StringIO()):
            self.assertEqual(jev_gate.run([]), 2)
        read_diff.assert_not_called()


class GateRepoTest(unittest.TestCase):
    """read_diff and run against a real scratch repo; Jev itself is never called."""

    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.git("init", "-q")
        (self.repo / "sub").mkdir()
        methods = "".join(f"    def m{i}(self, rows):\n        return rows\n\n" for i in range(150))
        (self.repo / "big.py").write_text("class Big:\n" + methods)
        (self.repo / "gone.py").write_text("x = 1\n")
        self.git("add", ".")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)

    def git(self, *args: str) -> None:
        subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)

    def test_a_change_deep_in_a_class_reaches_jev_and_untracked_files_are_root_relative(self) -> None:
        big = self.repo / "big.py"
        big.write_text(big.read_text().replace(
            "    def m140(self, rows):\n        return rows\n",
            "    def m140(self, rows):\n        return [r for r in rows if r in rows]\n"))
        (self.repo / "gone.py").unlink()
        (self.repo / "sub" / "new file.go").write_text("package x\n\n*p = 3\n//go:build linux\n// says why\nvar y = 1\n")
        os.chdir(self.repo / "sub")
        hunks = jev_gate.parse(jev_gate.read_diff(str(self.repo), None, []))
        items = jev_gate.items_for(hunks, request="speed up m140")
        self.assertEqual({hunk["file"] for hunk in hunks}, {"big.py", "sub/new file.go"})
        for item in items:
            if item["file"] == "big.py":
                text = item["state"].get("hunk") or item["state"].get("code")
                self.assertIn("r in rows if r in rows", text, item["gate"])
        comments = [item["state"]["comment"].strip() for item in items if item["gate"] == "comments"]
        self.assertEqual(comments, ["// says why"])

    def test_a_repo_without_commits_still_reads_its_files(self) -> None:
        empty = Path(tempfile.mkdtemp()).resolve()
        subprocess.run(["git", "-C", str(empty), "init", "-q"], check=True)
        (empty / "a.py").write_text("x = 1\n")
        os.chdir(empty)
        hunks = jev_gate.parse(jev_gate.read_diff(str(empty), None, []))
        self.assertEqual([hunk["file"] for hunk in hunks], ["a.py"])

    def test_a_subfolder_in_the_allowlist_does_not_open_the_whole_repo(self) -> None:
        os.chdir(self.repo / "sub")
        config = {**CONFIG, "hooks_allow": [str(self.repo / "sub")]}
        with mock.patch.object(jev_gate, "load_config", return_value=config), \
                mock.patch.object(jev_gate, "read_diff") as read_diff, redirect_stderr(io.StringIO()):
            self.assertEqual(jev_gate.run([]), 2)
        read_diff.assert_not_called()


PLAN = """# Plan

| Option | Role | Effort |
| --- | --- | --- |
| an earlier table that is not the task table | x | y |

| # | Task | Depends on | Files it writes | Role | Effort | Check |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Bump the version | none | `plugin.json` | chore | low | json.tool |
| 2 | Billing screen | 1 | `web/**` | Worker | High | visual gate |
| 3 | Payments sync | none | `payments/**` | payments-agent | its own | tests |

Done.
"""
MODEL_MAP = (Path(__file__).resolve().parents[3]
             / "roles/role-orchestrator/references/model-map.md")


class RouteTest(unittest.TestCase):
    def test_reads_the_last_table_with_task_role_and_effort(self) -> None:
        rows = jev_route.read_table(PLAN)
        self.assertEqual([row["#"] for row in rows], ["1", "2", "3"])
        self.assertEqual(rows[0]["files it writes"], "`plugin.json`")

    def test_an_escaped_pipe_stays_in_its_cell_and_a_short_row_is_refused(self) -> None:
        table = PLAN.replace("| 1 | Bump the version |", "| 1 | Parse a \\| b |")
        row = jev_route.read_table(table)[0]
        self.assertEqual((row["task"], row["role"], row["effort"]), ("Parse a | b", "chore", "low"))
        with self.assertRaises(jev_route.TableError):
            jev_route.read_table(PLAN.replace("| 1 | Bump the version | none |", "| 1 | Bump |"))

    def test_a_fenced_example_table_is_not_the_task_table(self) -> None:
        example = "\n```markdown\n" + PLAN.split("Done.")[0].split("\n\n", 2)[2] + "```\n"
        rows = jev_route.read_table(PLAN + example.replace("Bump the version", "Example only"))
        self.assertEqual(rows[0]["task"], "Bump the version")

    def test_verdicts(self) -> None:
        self.assertEqual(jev_route.verdict("worker-high", "worker-high", 0.9), "sure")
        self.assertEqual(jev_route.verdict("worker-high", "worker-high", 0.5), "sure, but close")
        self.assertEqual(jev_route.verdict("worker-high", "worker-medium", 0.9), "check the effort")
        self.assertTrue(jev_route.verdict("chore-low", "worker-medium", 0.9).startswith("UNSURE"))
        self.assertIn("project agent", jev_route.verdict("payments-agent-its own", "worker-high", 0.9))
        self.assertEqual(jev_route.option_of(" Worker", "High "), "worker-high")
        self.assertEqual(jev_route.option_of("`worker`", "medium (default)"), "worker-medium")
        self.assertEqual(jev_route.verdict("designer-xhigh", "designer-high", 0.9), "check the effort")
        self.assertTrue(jev_route.verdict("chore-high", "worker-high", 0.9).startswith("UNSURE"))
        self.assertIn("project agent", jev_route.verdict("worker-ui-high", "worker-high", 0.9))

    def test_models_match_the_model_map(self) -> None:
        section = MODEL_MAP.read_text().split("\n## Claude Code\n")[1].split("\n## ")[0]
        rows = re.findall(r"^\| (\w+) \| `(\w+)` \| `\w+` \|", section, re.M)
        self.assertEqual({role: model for role, model in rows if role != "Role"}, jev_route.MODELS)
        roles = {option.split("-")[0] for option in jev_route.OPTIONS} - {"unclear"}
        self.assertEqual(roles, set(jev_route.MODELS))

    def test_jev_never_sees_the_plans_own_pick(self) -> None:
        plan = Path(tempfile.mkdtemp()) / "plan.md"
        plan.write_text(PLAN)
        answer = {"answers": {"route": {"choice": "chore-low", "confidence": 0.9}}}
        config = {**CONFIG, "hooks_allow": [str(plan.parent)]}
        with mock.patch.object(jev_route, "load_config", return_value=config), \
                mock.patch.object(jev_route, "api_key", return_value="k"), \
                mock.patch.object(jev_route, "ask", return_value=answer) as ask, \
                redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
            self.assertEqual(jev_route.run([str(plan)]), 0)
        states = [call.args[0] for call in ask.call_args_list]
        self.assertEqual(len(states), 3)
        self.assertTrue(all(set(state) == {"task", "files", "check"} for state in states))
        self.assertIn("| 1 | Bump the version | chore-low | chore-low (0.90) | haiku | sure |", out.getvalue())

    def test_refuses_a_plan_outside_the_allowlist(self) -> None:
        plan = Path(tempfile.mkdtemp()) / "plan.md"
        plan.write_text(PLAN)
        with mock.patch.object(jev_route, "load_config", return_value=CONFIG), \
                mock.patch.object(jev_route, "ask") as ask, redirect_stderr(io.StringIO()):
            self.assertEqual(jev_route.run([str(plan)]), 2)
        ask.assert_not_called()


class AllowlistTest(unittest.TestCase):
    def test_only_the_folder_and_its_children(self) -> None:
        config = {"hooks_allow": ["/tmp/a"]}
        self.assertTrue(jev_client.is_allowed("/tmp/a", config))
        self.assertTrue(jev_client.is_allowed("/tmp/a/b", config))
        self.assertFalse(jev_client.is_allowed("/tmp/ab", config))

    def test_an_entry_that_cannot_be_trusted_opens_no_folder(self) -> None:
        home = str(Path.home())
        for entry in ["/", "~", home, ".", "", "relative/dir", 7, None]:
            config = {"hooks_allow": [entry]}
            self.assertFalse(jev_client.is_allowed("/tmp/anywhere", config), repr(entry))
            self.assertFalse(jev_client.is_allowed(home + "/code/x", config), repr(entry))

    def test_a_hooks_allow_that_is_not_a_list_opens_nothing(self) -> None:
        for value in ["~/code/some-repo", "/tmp/a", {"a": 1}, None]:
            self.assertFalse(jev_client.is_allowed("/tmp/a", {"hooks_allow": value}), repr(value))

    def test_a_good_entry_still_works_beside_a_bad_one(self) -> None:
        config = {"hooks_allow": ["/", "/tmp/a"]}
        self.assertTrue(jev_client.is_allowed("/tmp/a/b", config))
        self.assertFalse(jev_client.is_allowed("/tmp/other", config))


class LoadConfigTests(unittest.TestCase):
    """Defaults sit under the user's config, and only the user can open a folder."""

    def load(self, defaults: dict, own: dict | None) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            default_path, own_path = Path(tmp) / "defaults.json", Path(tmp) / "own.json"
            default_path.write_text(json.dumps(defaults))
            if own is not None:
                own_path.write_text(json.dumps(own))
            with mock.patch.object(jev_client, "DEFAULTS_PATH", default_path), mock.patch.object(
                jev_client, "CONFIG_PATH", own_path
            ):
                return jev_client.load_config()

    def test_defaults_fill_router_skills_and_thresholds(self):
        config = self.load({"router_threshold": 0.7, "router_skills": {"a": "A"}}, {"router_skills": {"b": "B"}})
        self.assertEqual(config["router_skills"], {"a": "A", "b": "B"})
        self.assertEqual(config["router_threshold"], 0.7)

    def test_hooks_allow_is_never_taken_from_the_defaults(self):
        self.assertEqual(self.load({"hooks_allow": ["/"]}, None)["hooks_allow"], [])
        self.assertEqual(self.load({"hooks_allow": ["/"]}, {"hooks_allow": ["/x"]})["hooks_allow"], ["/x"])

    def test_null_drops_a_default_skill_and_the_users_value_wins(self):
        config = self.load({"router_skills": {"a": "A", "b": "B"}}, {"router_skills": {"a": None, "b": "mine"}})
        self.assertEqual(config["router_skills"], {"b": "mine"})

    def test_a_config_that_is_not_an_object_is_ignored(self):
        self.assertEqual(self.load({"router_skills": {"a": "A"}}, [1, 2])["router_skills"], {"a": "A"})


class SetupTests(unittest.TestCase):
    """The allowlist helpers never guess: they keep other keys, skip duplicates, refuse a broken file."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name).resolve()
        (self.home / "code" / "app").mkdir(parents=True)
        self.config = self.home / ".claude" / "jev" / "config.json"
        for patcher in (
            mock.patch.object(jev_client, "CONFIG_PATH", self.config),
            mock.patch.dict("os.environ", {"HOME": str(self.home), "USERPROFILE": str(self.home)}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_allow_creates_the_file_and_stores_a_home_relative_entry(self) -> None:
        self.assertEqual(jev_setup.allow(str(self.home / "code" / "app")), "allowed: ~/code/app")
        self.assertEqual(json.loads(self.config.read_text()), {"hooks_allow": ["~/code/app"]})

    def test_allow_keeps_the_other_keys(self) -> None:
        self.config.parent.mkdir(parents=True)
        self.config.write_text(json.dumps({"router_skills": {"a": "A"}, "hooks_allow": ["/elsewhere"]}))
        jev_setup.allow(str(self.home / "code"))
        saved = json.loads(self.config.read_text())
        self.assertEqual(saved["router_skills"], {"a": "A"})
        self.assertEqual(saved["hooks_allow"], ["/elsewhere", "~/code"])

    def test_allow_skips_a_folder_already_covered_by_a_parent(self) -> None:
        jev_setup.allow(str(self.home / "code"))
        self.assertIn("covered by ~/code", jev_setup.allow(str(self.home / "code" / "app")))
        self.assertEqual(jev_setup.allowed(), ["~/code"])

    def test_allow_refuses_a_missing_folder_and_the_home_folder(self) -> None:
        for folder in (self.home / "nope", self.home):
            with self.assertRaises(jev_setup.ConfigError):
                jev_setup.allow(str(folder))
        self.assertFalse(self.config.exists())

    def test_a_config_that_does_not_parse_is_never_overwritten(self) -> None:
        self.config.parent.mkdir(parents=True)
        self.config.write_text("{oops")
        with self.assertRaises(jev_setup.ConfigError):
            jev_setup.allow(str(self.home / "code"))
        self.assertEqual(self.config.read_text(), "{oops")

    def test_setup_allows_the_folders_typed_until_a_blank_line(self) -> None:
        answers = iter([str(self.home / "code" / "app"), "/no/such/folder", ""])
        with mock.patch.object(jev_setup, "_key_step"), redirect_stdout(io.StringIO()) as out:
            jev_setup.setup(lambda _prompt: next(answers))
        self.assertEqual(jev_setup.allowed(), ["~/code/app"])
        self.assertIn("is not a folder", out.getvalue())

    def test_run_dispatches_the_commands_and_rejects_a_missing_argument(self) -> None:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(jev_setup.run("allow", [], check=lambda: 0), 2)
            self.assertEqual(jev_setup.run("allow", [str(self.home / "code")], check=lambda: 0), 0)
            self.assertEqual(jev_setup.run("allowed", [], check=lambda: 0), 0)
            with mock.patch.object(jev_setup, "setup"):
                self.assertEqual(jev_setup.run("setup", [], check=lambda: 7), 7)


class KeyLookupTests(unittest.TestCase):
    """Environment first, then the key file, then the Keychain, and each says where it came from."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.key_path = Path(tmp.name) / "key"
        for patcher in (
            mock.patch.object(jev_client, "KEY_PATH", self.key_path),
            mock.patch.dict("os.environ", {}, clear=True),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def keychain_holds(self, key: str, returncode: int = 0):
        done = subprocess.CompletedProcess([], returncode, stdout=key + "\n", stderr="")
        return mock.patch("subprocess.run", return_value=done)

    def test_the_environment_wins_over_the_file(self) -> None:
        self.key_path.write_text("from-file\n")
        with mock.patch.dict("os.environ", {"TYPESAFE_API_KEY": " from-env "}):
            self.assertEqual(jev_client.find_key(), ("environment", "from-env"))

    def test_the_key_file_beats_the_keychain_and_is_trimmed(self) -> None:
        self.key_path.write_text("  from-file\n")
        with self.keychain_holds("from-keychain"):
            self.assertEqual(jev_client.find_key(), ("key file", "from-file"))

    def test_the_keychain_is_the_last_resort(self) -> None:
        with self.keychain_holds("from-keychain"):
            self.assertEqual(jev_client.find_key(), ("Keychain", "from-keychain"))

    def test_no_source_raises(self) -> None:
        with self.keychain_holds("", returncode=44):
            with self.assertRaises(JevError):
                jev_client.find_key()

    def test_key_stores_a_private_file_where_there_is_no_keychain(self) -> None:
        with mock.patch.object(sys, "platform", "linux"), redirect_stdout(io.StringIO()):
            jev_setup.store_key(lambda _prompt: "  secret  ")
        self.assertEqual(self.key_path.read_text(), "secret\n")
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.key_path.stat().st_mode), 0o600)

    def test_key_tightens_a_file_that_was_readable_by_others(self) -> None:
        self.key_path.write_text("old\n")
        self.key_path.chmod(0o644)
        with mock.patch.object(sys, "platform", "linux"), redirect_stdout(io.StringIO()):
            jev_setup.store_key(lambda _prompt: "new")
        self.assertEqual(self.key_path.read_text(), "new\n")
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.key_path.stat().st_mode), 0o600)

    def test_an_empty_key_is_not_stored(self) -> None:
        with mock.patch.object(sys, "platform", "linux"), redirect_stdout(io.StringIO()):
            jev_setup.store_key(lambda _prompt: "   ")
        self.assertFalse(self.key_path.exists())

    def test_setup_asks_for_the_key_only_when_none_is_found(self) -> None:
        ask_secret = mock.Mock(return_value="typed")
        with mock.patch.object(sys, "platform", "linux"), self.keychain_holds("", returncode=44):
            with mock.patch.object(jev_setup, "allowed", return_value=[]), redirect_stdout(io.StringIO()):
                jev_setup.setup(lambda _prompt: "", ask_secret)
        self.assertEqual(ask_secret.call_count, 1)
        self.assertEqual(self.key_path.read_text(), "typed\n")
        with redirect_stdout(io.StringIO()) as out:
            jev_setup.setup(lambda _prompt: "", ask_secret)
        self.assertEqual(ask_secret.call_count, 1)
        self.assertIn("found (key file)", out.getvalue())


class PortabilityTests(unittest.TestCase):
    def test_a_machine_without_the_keychain_reports_no_key_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch.object(jev_client, "KEY_PATH", Path(tmp) / "key"):
                with mock.patch("subprocess.run", side_effect=FileNotFoundError):
                    with self.assertRaises(JevError):
                        jev_client.api_key()

    def test_shell_scripts_have_no_carriage_returns(self) -> None:
        for script in (Path(__file__).resolve().parents[4] / "hooks").glob("*.sh"):
            self.assertNotIn(b"\r", script.read_bytes(), script.name)

    def test_every_python_hook_falls_back_to_python_when_python3_is_unusable(self) -> None:
        path = Path(__file__).resolve().parents[4] / "hooks" / "hooks.json"
        groups = json.loads(path.read_text())["hooks"].values()
        commands = [h["command"] for group in groups for entry in group for h in entry["hooks"] if ".py" in h["command"]]
        for script in ("hook_router.py", "hook_stop.py"):
            self.assertTrue(any(script in command for command in commands), script)
        for command in commands:
            self.assertIn("else exec python ", command)


class SessionCheckTest(unittest.TestCase):
    """check-jev.sh must not nag an install that never set Jev up, nor reach Jev outside an allowed folder."""

    REPO = Path(__file__).resolve().parents[4]

    def run_check(self, config: str | None) -> str:
        with tempfile.TemporaryDirectory() as home:
            if config is not None:
                folder = Path(home) / ".claude" / "jev"
                folder.mkdir(parents=True)
                (folder / "config.json").write_text(config)
            env = {"PATH": os.environ["PATH"], "HOME": home, "CLAUDE_PLUGIN_ROOT": str(self.REPO)}
            result = subprocess.run(["bash", str(self.REPO / "hooks" / "check-jev.sh")], cwd=home, env=env,
                                    capture_output=True, text=True, timeout=30)
        return result.stdout

    def test_no_config_at_all_is_silent(self) -> None:
        self.assertEqual(self.run_check(None), "")

    def test_a_config_with_nothing_allowed_says_so(self) -> None:
        self.assertIn("no folder is allowlisted", self.run_check('{"hooks_allow": []}'))

    def test_a_hooks_allow_that_is_a_string_is_silent_and_opens_nothing(self) -> None:
        self.assertEqual(self.run_check('{"hooks_allow": "~/code/some-repo"}'), "")

    def test_a_folder_outside_the_allowlist_is_silent(self) -> None:
        self.assertEqual(self.run_check('{"hooks_allow": ["/tmp/jev-tests-allowed"]}'), "")
