"""Check that only intended task fields leave evaluator records."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

DIRECTORY = Path(__file__).resolve().parents[2] / "scripts/arcade"
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location("prepare_tasks", DIRECTORY / "prepare_tasks.py")
prepare_tasks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare_tasks)
sys.path.remove(str(DIRECTORY))


class PrepareTasksTest(unittest.TestCase):
    def test_whitelist_and_exclusive_output(self):
        row = {"instance_id": "safe", "repo": "public/repo", "base_commit": "a" * 40,
               "problem_statement": "task", "patch": "GOLD_MARKER",
               "test_patch": "GOLD_TEST_MARKER", "all_patch": "GOLD_ALL_MARKER",
               "PASS_TO_PASS": ["GOLD_TEST_NAMES"], "other": "SECRET_MARKER"}
        with tempfile.TemporaryDirectory() as directory, patch.object(
                prepare_tasks.prepare_dataset, "read_records", return_value=[row]):
            target = Path(directory) / "tasks"
            self.assertEqual(prepare_tasks.prepare(Path("unused"), target), 1)
            data = (target / "safe.json").read_text()
            self.assertEqual(json.loads(data), {key: row[key] for key in
                             ("instance_id", "repo", "base_commit", "problem_statement")})
            self.assertNotIn("MARKER", data)
            self.assertNotIn("GOLD_TEST_NAMES", data)
            self.assertEqual(target.stat().st_mode & 0o777, 0o700)
            self.assertEqual((target / "safe.json").stat().st_mode & 0o777, 0o600)
            with self.assertRaisesRegex(ValueError, "already exists"):
                prepare_tasks.prepare(Path("unused"), target)

    def test_dataset_error_never_creates_output(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(
                prepare_tasks.prepare_dataset, "read_records", side_effect=ValueError("bad hash")):
            target = Path(directory) / "tasks"
            with self.assertRaisesRegex(ValueError, "bad hash"):
                prepare_tasks.prepare(Path("unused"), target)
            self.assertFalse(target.exists())

    def test_checkout_or_symlink_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "link"
            target.symlink_to(Path(directory) / "missing")
            for output in (target, prepare_tasks.prepare_dataset.ROOT / "task-inputs-test"):
                with self.assertRaises(ValueError):
                    prepare_tasks.prepare(Path("unused"), output)


if __name__ == "__main__":
    unittest.main()
