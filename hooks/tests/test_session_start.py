"""Run the SessionStart command that injects the Golden Rules, on a machine with nothing installed."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Claude Code replaces a longer hook stdout with a 2,000-character preview and never asks
# the model to read the rest (code.claude.com/docs/en/hooks, read 2026-11-11).
STDOUT_CAP = 10_000


class SessionStartOutput(unittest.TestCase):
    def setUp(self) -> None:
        hooks = json.loads((ROOT / "hooks" / "hooks.json").read_text())
        command = hooks["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        with tempfile.TemporaryDirectory() as empty:
            env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(ROOT), "HOME": empty}
            self.out = subprocess.run(["bash", "-c", command], cwd=empty, env=env,
                                      capture_output=True, text=True, check=True).stdout

    def test_rules_and_every_warning_fit_under_the_cap(self) -> None:
        self.assertIn("# Golden Rules", self.out)
        self.assertIn("superpowers is not installed", self.out)
        self.assertLess(len(self.out), STDOUT_CAP)

    def test_optional_egm_is_not_reported_missing(self) -> None:
        self.assertNotIn("EGM", self.out.split("Note for the agent", 1)[1])


if __name__ == "__main__":
    unittest.main()
