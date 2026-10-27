#!/usr/bin/env python3
"""Create or verify a task identity manifest against the pinned dataset.

The dataset contains evaluator-only answers. This script emits only the task
ID, repository and base commit; keep the dataset itself away from the agent.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

import prepare_dataset


def identities(dataset):
    rows = prepare_dataset.read_records(dataset)
    return sorted(
        ({"id": row["instance_id"], "repo": row["repo"], "base_commit": row["base_commit"]}
         for row in rows),
        key=lambda row: row["id"],
    )


def verify(manifest, dataset):
    data = Path(manifest).read_bytes()
    value = json.loads(data.decode("utf-8"),
                       object_pairs_hook=prepare_dataset.object_without_duplicate_keys)
    if not isinstance(value, dict) or set(value) != {"tasks"} or not isinstance(value["tasks"], list):
        raise ValueError("manifest must contain only a tasks list")
    tasks = value["tasks"]
    if any(not isinstance(row, dict) or set(row) != {"id", "repo", "base_commit"}
           or any(not isinstance(row[key], str) for key in row) for row in tasks):
        raise ValueError("manifest task must contain only string id, repo and base_commit")
    if sorted(tasks, key=lambda row: row["id"]) != identities(dataset):
        raise ValueError("manifest does not match pinned dataset task identities and base commits")
    return hashlib.sha256(data).hexdigest()


def create(dataset, output):
    tasks = identities(dataset)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump({"tasks": tasks}, file, ensure_ascii=False, sort_keys=True, indent=2)
            file.write("\n")
    except BaseException:
        Path(output).unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "verify"))
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == "create":
            create(args.dataset, args.manifest)
        else:
            verify(args.manifest, args.dataset)
    except (OSError, UnicodeError, ValueError) as error:
        parser.exit(1, f"cohort: {error}\n")
    print("Pinned task identities and base commits: 48. No evaluator answers emitted.")


if __name__ == "__main__":
    main()
