"""Verify cohort binding without exporting evaluator-only fields."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

DIRECTORY = Path(__file__).resolve().parents[2] / "scripts/arcade"
sys.path.insert(0, str(DIRECTORY))
spec = importlib.util.spec_from_file_location("cohort", DIRECTORY / "cohort.py")
cohort = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cohort)
sys.path.remove(str(DIRECTORY))


class CohortTest(unittest.TestCase):
    def test_clean_manifest_drops_gold_and_rejects_tampering(self):
        rows = [
            {"instance_id": "a", "repo": "one/repo", "base_commit": "a" * 40,
             "patch": "GOLD_MARKER", "test_patch": "GOLD_TEST_MARKER"},
            {"instance_id": "b", "repo": "two/repo", "base_commit": "b" * 40},
        ]
        with tempfile.TemporaryDirectory() as directory, patch.object(
                cohort.prepare_dataset, "read_records", return_value=rows):
            manifest = Path(directory) / "manifest.json"
            cohort.create(Path("unused"), manifest)
            original = manifest.read_text()
            self.assertNotIn("GOLD", original)
            cohort.verify(manifest, Path("unused"))
            with self.assertRaises(FileExistsError):
                cohort.create(Path("unused"), manifest)
            for change in ("id", "repo", "base_commit"):
                value = json.loads(original)
                value["tasks"][0][change] = "changed"
                manifest.write_text(json.dumps(value))
                with self.assertRaisesRegex(ValueError, "does not match"):
                    cohort.verify(manifest, Path("unused"))
            value = json.loads(original)
            value["tasks"][0]["patch"] = "GOLD_MARKER"
            manifest.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "only string"):
                cohort.verify(manifest, Path("unused"))

    def test_invalid_dataset_never_creates_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            with patch.object(cohort.prepare_dataset, "read_records", side_effect=ValueError("bad hash")):
                with self.assertRaisesRegex(ValueError, "bad hash"):
                    cohort.create(Path("unused"), manifest)
            self.assertFalse(manifest.exists())


if __name__ == "__main__":
    unittest.main()
