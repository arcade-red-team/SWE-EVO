#!/usr/bin/env python3
"""Convert an explicit task manifest and JSONL patches to SWE-agent preds.json.

Manifest: {"tasks": [{"id": "...", "repo": "..."}, ...]}.
Each JSONL row: {"task_id": "...", "model_patch": "..."}; an optional
"status", if supplied, must be "completed". A string may be empty: it is an
explicit no-change patch, not an absent or failed trajectory. This adapter
validates identities and format, not patch correctness or evaluator outcomes.
"""

import argparse
import json
import os
import re
from pathlib import Path

ID_PATTERN = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*\Z")


def object_without_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_json(value):
    return json.loads(value, object_pairs_hook=object_without_duplicate_keys)


def predictions(manifest_path: Path, records_path: Path):
    manifest = read_json(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("tasks"), list):
        raise ValueError("manifest must contain a tasks list")
    tasks = set()
    for task in manifest["tasks"]:
        task_id = task.get("id") if isinstance(task, dict) else None
        if not isinstance(task_id, str) or not ID_PATTERN.fullmatch(task_id) or task_id in tasks:
            raise ValueError("manifest contains an invalid or duplicate task ID")
        tasks.add(task_id)
    if not tasks:
        raise ValueError("manifest must contain at least one task")

    result = {}
    for line in records_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            raise ValueError("records contain a blank JSONL line")
        row = read_json(line)
        if not isinstance(row, dict):
            raise ValueError("record must be an object")
        task_id = row.get("task_id")
        if not isinstance(task_id, str) or task_id not in tasks:
            raise ValueError("record has an unknown task ID")
        if task_id in result:
            raise ValueError("records contain a duplicate task ID")
        if "status" in row and row["status"] != "completed":
            raise ValueError("record is not completed")
        model_patch = row.get("model_patch")
        if not isinstance(model_patch, str):
            raise ValueError("record has a missing or invalid model patch")
        # Retain only the prediction field, never task metadata or gold fields.
        result[task_id] = {"model_patch": model_patch}
    if result.keys() != tasks:
        raise ValueError("records do not cover the explicit manifest")
    return result


def prepare(manifest: Path, records: Path, output: Path):
    result = predictions(manifest, records)
    # O_EXCL prevents overwriting an existing file, including a symlink.
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(result, file, ensure_ascii=False, sort_keys=True)
            file.write("\n")
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return len(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new preds.json path")
    args = parser.parse_args()
    try:
        count = prepare(args.manifest, args.records, args.output)
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(1, f"prepare_predictions: {error}\n")
    print(f"Prepared {count} predictions for the explicit manifest; evaluator not run.")


if __name__ == "__main__":
    main()
