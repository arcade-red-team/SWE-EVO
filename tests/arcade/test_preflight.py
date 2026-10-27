"""Fail-closed checks for the SWE-EVO preflight."""

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/arcade/preflight.py"
spec = importlib.util.spec_from_file_location("arcade_preflight", SCRIPT)
assert spec and spec.loader
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PreflightTest(unittest.TestCase):
    def test_login_status_can_be_reported_on_stderr(self):
        result = subprocess.CompletedProcess([], 0, "", "Logged in using ChatGPT\n")
        with patch.object(preflight.subprocess, "run", return_value=result):
            ok, text = preflight.command(["codex", "login", "status"], Path("."))
        self.assertTrue(ok)
        self.assertEqual(text, "Logged in using ChatGPT")

    @staticmethod
    def command_control(args, root):
        if args[:3] == ["codex", "login", "status"]:
            return True, "Logged in using ChatGPT"
        return True, "linux/amd64"

    def test_complete_input_control(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for relative in ("SWE-bench/evaluate_instance.py",):
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}\n", encoding="utf-8")
            inputs = root / "output_final"
            inputs.mkdir()
            for number in range(48):
                (inputs / f"{number}.json").write_text(
                    json.dumps({"instance_id": str(number)}), encoding="utf-8"
                )
            with patch.object(preflight, "command", side_effect=self.command_control):
                results = preflight.check(root, inputs)
        self.assertTrue(all(passed for _, passed, _ in results))

    def test_missing_files_are_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(preflight, "command", return_value=(True, "linux/amd64")):
                results = preflight.check(Path(directory))
        statuses = {name: passed for name, passed, _ in results}
        self.assertFalse(statuses["SWE-EVO evaluator"])
        self.assertFalse(statuses["Evaluator instance JSON count and unique IDs"])

    def test_incomplete_evaluator_inputs_are_not_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = root / "output_final"
            inputs.mkdir()
            for number in range(47):
                (inputs / f"{number}.json").write_text(
                    json.dumps({"instance_id": str(number)}), encoding="utf-8"
                )
            with patch.object(preflight, "command", return_value=(True, "linux/amd64")):
                results = preflight.check(root, inputs)
        statuses = {name: passed for name, passed, _ in results}
        self.assertFalse(statuses["Evaluator instance JSON count and unique IDs"])

    def test_unverified_checks_cannot_report_ready(self):
        with patch.object(preflight, "check", return_value=[("example", True, "")]):
            with patch("sys.argv", [str(SCRIPT)]):
                self.assertEqual(preflight.main(), 1)


if __name__ == "__main__":
    unittest.main()
