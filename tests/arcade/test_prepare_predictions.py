"""Tests for explicit SWE-agent prediction export."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/arcade/prepare_predictions.py"
spec = importlib.util.spec_from_file_location("prepare_predictions", SCRIPT)
assert spec and spec.loader
prepare_predictions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare_predictions)


class PreparePredictionsTest(unittest.TestCase):
    def test_subset_empty_patch_and_no_metadata_leak(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            records = root / "patches.jsonl"
            output = root / "preds.json"
            manifest.write_text(json.dumps({"tasks": [{"id": "a"}, {"id": "b"}]}))
            rows = [
                {"task_id": "a", "model_patch": "diff --git a/x b/x\n", "status": "completed", "gold": "hidden"},
                {"task_id": "b", "model_patch": ""},
            ]
            records.write_text("".join(json.dumps(row) + "\n" for row in rows))
            self.assertEqual(prepare_predictions.prepare(manifest, records, output), 2)
            self.assertEqual(json.loads(output.read_text()), {
                "a": {"model_patch": "diff --git a/x b/x\n"}, "b": {"model_patch": ""},
            })
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            before = output.read_bytes()
            with self.assertRaises(FileExistsError):
                prepare_predictions.prepare(manifest, records, output)
            self.assertEqual(output.read_bytes(), before)

    def test_missing_duplicate_unknown_invalid_patch_and_status_fail_closed(self):
        cases = [
            ([{"task_id": "a", "model_patch": ""}], "cover"),
            ([{"task_id": "a", "model_patch": ""}] * 2, "duplicate"),
            ([{"task_id": "x", "model_patch": ""}], "unknown"),
            ([{"task_id": "a", "model_patch": None}], "patch"),
            ([{"task_id": "a", "model_patch": "", "status": "failed"}], "completed"),
        ]
        for rows, message in cases:
            with self.subTest(message=message), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                manifest, records, output = root / "manifest", root / "records", root / "preds"
                ids = ["a", "b"] if message == "cover" else ["a"]
                manifest.write_text(json.dumps({"tasks": [{"id": x} for x in ids]}))
                records.write_text("".join(json.dumps(row) + "\n" for row in rows))
                with self.assertRaisesRegex(ValueError, message):
                    prepare_predictions.prepare(manifest, records, output)
                self.assertFalse(output.exists())

    def test_bad_manifest_and_duplicate_json_keys(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, records, output = root / "manifest", root / "records", root / "preds"
            records.write_text('{"task_id":"a","model_patch":"","model_patch":"gold"}\n')
            for tasks in ([{"id": "a"}, {"id": "a"}], [{"id": "../escape"}], []):
                manifest.write_text(json.dumps({"tasks": tasks}))
                with self.assertRaises(ValueError):
                    prepare_predictions.prepare(manifest, records, output)
                self.assertFalse(output.exists())
            manifest.write_text(json.dumps({"tasks": [{"id": "a"}]}))
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                prepare_predictions.prepare(manifest, records, output)
            self.assertFalse(output.exists())

    def test_symlink_output_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest, records, target, output = root / "manifest", root / "records", root / "target", root / "preds"
            manifest.write_text(json.dumps({"tasks": [{"id": "a"}]}))
            records.write_text(json.dumps({"task_id": "a", "model_patch": ""}) + "\n")
            target.write_text("preserve")
            output.symlink_to(target)
            with self.assertRaises(FileExistsError):
                prepare_predictions.prepare(manifest, records, output)
            self.assertEqual(target.read_text(), "preserve")


if __name__ == "__main__":
    unittest.main()
