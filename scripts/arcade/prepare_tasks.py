#!/usr/bin/env python3
"""Extract benchmark task inputs, without evaluator fields, into a new directory.

Task statements remain benchmark-provided content and may overlap with patches;
this extractor does not establish isolation or remove such overlap.
"""

import argparse
import json
import os
import shutil
from pathlib import Path

import prepare_dataset


def prepare(dataset: Path, output: Path) -> int:
    if output.name in ("", ".", "..") or output.exists() or output.is_symlink():
        raise ValueError("output directory already exists or is unsafe")
    parent = output.parent.resolve(strict=True)
    target = parent / output.name
    if target == prepare_dataset.ROOT or prepare_dataset.ROOT in target.parents:
        raise ValueError("output directory must be outside the checkout")
    if not parent.is_dir():
        raise ValueError("output parent must be a directory")
    rows = prepare_dataset.read_records(dataset)
    target.mkdir(mode=0o700)
    try:
        for row in rows:
            task = {key: row[key] for key in ("instance_id", "repo", "base_commit", "problem_statement")}
            path = target / (row["instance_id"] + ".json")
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(task, file, ensure_ascii=False, sort_keys=True)
                file.write("\n")
    except BaseException:
        shutil.rmtree(target)
        raise
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path, help="local pinned evaluator-only JSONL")
    parser.add_argument("output", type=Path, help="new task-input directory outside the checkout")
    args = parser.parse_args()
    try:
        count = prepare(args.dataset, args.output)
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(1, f"prepare_tasks: {error}\n")
    print(f"Prepared {count} task inputs; filesystem and prompt isolation remain unverified.")


if __name__ == "__main__":
    main()
