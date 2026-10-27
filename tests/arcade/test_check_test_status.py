"""Fail-closed independent checks of parsed benchmark test outcomes."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/arcade/check_test_status.py"
spec = importlib.util.spec_from_file_location("check_test_status", SCRIPT)
assert spec and spec.loader
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
GOLD = {"FAIL_TO_PASS": ["new_a", "new_b"], "PASS_TO_PASS": ["old"]}


class TestStatusAudit(unittest.TestCase):
    def test_clean_and_failures(self):
        outcomes = (
            ({"new_a": "PASSED", "new_b": "PASSED", "old": "PASSED"}, True, 1.0),
            ({"new_a": "PASSED", "new_b": "FAILED", "old": "PASSED"}, False, 0.5),
            ({"new_a": "PASSED", "new_b": "ERROR", "old": "ERROR"}, False, 0.0),
        )
        for statuses, resolved, fix in outcomes:
            with self.subTest(statuses=statuses):
                result = checker.audit(GOLD, statuses)
                self.assertEqual(result["status"], "scorable")
                self.assertEqual(result["resolved"], resolved)
                self.assertEqual(result["strict_fix_rate"], fix)

    def test_missing_skipped_xfail_and_unknown_are_unscorable(self):
        for value in (None, "SKIPPED", "XFAIL", "XPASS", "unexpected"):
            with self.subTest(value=value):
                statuses = {"new_a": "PASSED", "new_b": "PASSED", "old": "PASSED"}
                if value is None:
                    del statuses["old"]
                else:
                    statuses["old"] = value
                result = checker.audit(GOLD, statuses)
                self.assertEqual(result["status"], "unscorable")
                self.assertIsNone(result["resolved"])
                self.assertIsNone(result["strict_fix_rate"])
                self.assertEqual(result["groups"]["PASS_TO_PASS"]["tests"][0]["status"], value)

    def test_empty_old_test_list_is_no_coverage(self):
        gold = {"FAIL_TO_PASS": ["new_a"], "PASS_TO_PASS": []}
        result = checker.audit(gold, {"new_a": "PASSED"})
        self.assertEqual(result["groups"]["PASS_TO_PASS"]["coverage"], "no_coverage")
        self.assertEqual(result["unscorable_reasons"][0]["reason"], "no_coverage")
        self.assertEqual(result["status"], "unscorable")
        self.assertIsNone(result["resolved"])
        self.assertIsNone(result["strict_fix_rate"])

    def test_duplicate_expected_names_and_invalid_input_fail_closed(self):
        bad = (
            {"FAIL_TO_PASS": ["a", "a"], "PASS_TO_PASS": []},
            {"FAIL_TO_PASS": ["a"], "PASS_TO_PASS": ["a"]},
            {"FAIL_TO_PASS": ["a"], "PASS_TO_PASS": [None]},
        )
        for gold in bad:
            with self.subTest(gold=gold), self.assertRaises(ValueError):
                checker.audit(gold, {})
        with self.assertRaises(ValueError):
            checker.audit(GOLD, {"new_a": None})

    def test_cli_json_exit_and_duplicate_json_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            gold, statuses = root / "gold.json", root / "statuses.json"
            gold.write_text(json.dumps(GOLD))
            statuses.write_text(json.dumps({"new_a": "PASSED", "new_b": "PASSED", "old": "SKIPPED"}))
            cmd = [sys.executable, str(SCRIPT), "--gold", str(gold), "--statuses", str(statuses)]
            process = subprocess.run(cmd, text=True, capture_output=True, check=False)
            self.assertEqual(process.returncode, 1)
            self.assertEqual(json.loads(process.stdout)["status"], "unscorable")
            statuses.write_text('{"old":"PASSED","old":"FAILED"}')
            process = subprocess.run(cmd, text=True, capture_output=True, check=False)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(process.stdout, "")
            self.assertIn("duplicate JSON key", process.stderr)

    def test_extra_tests_are_not_silently_counted_as_expected(self):
        result = checker.audit(GOLD, {"new_a": "PASSED", "new_b": "PASSED", "old": "PASSED", "extra": "SKIPPED"})
        self.assertEqual(result["extra_parsed_tests"], 1)
        self.assertEqual(result["status"], "scorable")
        self.assertTrue(result["resolved"])


if __name__ == "__main__":
    unittest.main()
