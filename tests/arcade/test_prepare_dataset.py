"""Checks for pinned, private evaluator dataset preparation."""

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/arcade/prepare_dataset.py"
spec = importlib.util.spec_from_file_location("prepare_dataset", SCRIPT)
assert spec and spec.loader
prepare_dataset = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare_dataset)


def records():
    result = []
    for repo, count in prepare_dataset.REPOSITORIES.items():
        for number in range(count):
            result.append({
                "instance_id": repo.replace("/", "__") + "_" + str(number),
                "repo": repo,
                "base_commit": "a" * 40,
                "image": "example/image",
                "test_patch": "test patch",
                "patch": "gold patch",
                "problem_statement": "task",
                "end_version": "1.0",
                "FAIL_TO_PASS": ["test_new"],
                "PASS_TO_PASS": ["test_old"],
            })
    return result


def write_data(path, rows):
    data = "".join(json.dumps(row) + "\n" for row in rows).encode()
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


class PrepareDatasetTest(unittest.TestCase):
    def test_valid_records_are_private_and_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset, output = root / "input.jsonl", root / "evaluator"
            rows = records()
            rows[0]["test_patch"] = ""  # The pinned dataset includes an empty test patch.
            digest = write_data(dataset, rows)
            with patch.object(prepare_dataset, "DATASET_SHA256", digest):
                self.assertEqual(prepare_dataset.prepare(dataset, output), 48)
                self.assertEqual(len(list(output.glob("*.json"))), 48)
                self.assertEqual(json.loads((output / (rows[0]["instance_id"] + ".json")).read_text()), rows[0])
                self.assertEqual(output.stat().st_mode & 0o777, 0o700)
                self.assertEqual(next(output.glob("*.json")).stat().st_mode & 0o777, 0o600)
                with self.assertRaises(ValueError):
                    prepare_dataset.prepare(dataset, output)

    def test_tampered_data_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dataset, output = root / "input.jsonl", root / "evaluator"
            write_data(dataset, records())
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                prepare_dataset.prepare(dataset, output)
            self.assertFalse(output.exists())

    def test_duplicate_and_traversal_ids_are_rejected_before_writes(self):
        for malicious in ("duplicate", "../escape"):
            with self.subTest(malicious=malicious), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                dataset, output = root / "input.jsonl", root / "evaluator"
                rows = records()
                rows[1]["instance_id"] = rows[0]["instance_id"] if malicious == "duplicate" else malicious
                digest = write_data(dataset, rows)
                with patch.object(prepare_dataset, "DATASET_SHA256", digest):
                    with self.assertRaisesRegex(ValueError, "instance ID"):
                        prepare_dataset.prepare(dataset, output)
                self.assertFalse(output.exists())
                self.assertFalse((root / "escape.json").exists())

    def test_output_inside_checkout_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / "input.jsonl"
            digest = write_data(dataset, records())
            with patch.object(prepare_dataset, "DATASET_SHA256", digest):
                with self.assertRaisesRegex(ValueError, "outside the checkout"):
                    prepare_dataset.prepare(dataset, prepare_dataset.ROOT / "evaluator-data-test")


if __name__ == "__main__":
    unittest.main()
