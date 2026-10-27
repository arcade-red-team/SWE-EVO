#!/usr/bin/env python3
"""Prepare pinned SWE-EVO evaluator records outside the checkout."""

import argparse
import hashlib
import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATASET_SHA256 = "a5dc7fccf7d839140e2005b09937e0f83910a61518027ef72d42134542246f87"
REPOSITORIES = {
    "iterative/dvc": 26,
    "dask/dask": 8,
    "psf/requests": 4,
    "pydantic/pydantic": 3,
    "modin-project/modin": 3,
    "conan-io/conan": 2,
    "scikit-learn/scikit-learn": 2,
}
ID_PATTERN = re.compile(r"[A-Za-z0-9_-][A-Za-z0-9_.-]*\Z")
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
STRING_FIELDS = (
    "instance_id", "repo", "base_commit", "image",
    "patch", "problem_statement", "end_version",
)


def object_without_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_records(path: Path):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != DATASET_SHA256:
        raise ValueError("dataset SHA-256 does not match the pinned revision")
    records = []
    seen = set()
    for line in data.decode("utf-8").splitlines():
        if not line.strip():
            raise ValueError("empty JSONL record")
        row = json.loads(line, object_pairs_hook=object_without_duplicate_keys)
        if not isinstance(row, dict):
            raise ValueError("record must be an object")
        if any(not isinstance(row.get(key), str) or not row[key] for key in STRING_FIELDS):
            raise ValueError("record has a missing or invalid required string")
        if not isinstance(row.get("test_patch"), str):
            raise ValueError("record has an invalid test patch")
        instance_id = row["instance_id"]
        if not ID_PATTERN.fullmatch(instance_id) or instance_id in seen:
            raise ValueError("unsafe or duplicate instance ID")
        if not SHA_PATTERN.fullmatch(row["base_commit"]):
            raise ValueError("invalid base commit")
        for key in ("FAIL_TO_PASS", "PASS_TO_PASS"):
            tests = row.get(key)
            if not isinstance(tests, list) or any(not isinstance(test, str) or not test for test in tests):
                raise ValueError("invalid test list")
        if not row["FAIL_TO_PASS"]:
            raise ValueError("empty FAIL_TO_PASS")
        seen.add(instance_id)
        records.append(row)
    if len(records) != 48 or Counter(row["repo"] for row in records) != REPOSITORIES:
        raise ValueError("unexpected instance count or repository distribution")
    return records


def prepare(dataset: Path, output: Path):
    # Reject both existing targets and targets whose parent resolves into the checkout.
    if output.name in ("", ".", "..") or output.exists() or output.is_symlink():
        raise ValueError("output directory already exists or is unsafe")
    parent = output.parent.resolve(strict=True)
    target = parent / output.name
    if target == ROOT or ROOT in target.parents:
        raise ValueError("output directory must be outside the checkout")
    if not parent.is_dir():
        raise ValueError("output parent must be a directory")
    records = read_records(dataset)
    # mkdir is exclusive: never take ownership of an existing target.
    target.mkdir(mode=0o700)
    try:
        for row in records:
            path = target / (row["instance_id"] + ".json")
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(row, file, ensure_ascii=False, sort_keys=True)
                file.write("\n")
    except BaseException:
        shutil.rmtree(target)
        raise
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="local pinned test.jsonl")
    parser.add_argument("output", type=Path, help="new evaluator-only directory outside the checkout")
    args = parser.parse_args()
    try:
        count = prepare(args.dataset, args.output)
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(1, f"prepare_dataset: {error}\n")
    print(f"Prepared {count} evaluator-only records; keep this directory inaccessible to the agent.")


if __name__ == "__main__":
    main()
