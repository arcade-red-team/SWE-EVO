#!/usr/bin/env python3
"""Audit parsed test statuses independently of the upstream evaluator.

Inputs: a gold JSON object containing FAIL_TO_PASS and PASS_TO_PASS arrays,
plus a JSON object mapping test names to the raw parsed status strings. This
checks reporting completeness; it does not run tests or verify log provenance.
"""

import argparse
import json
import sys
from pathlib import Path


SCHEMA_VERSION = 1
TEST_GROUPS = ("FAIL_TO_PASS", "PASS_TO_PASS")
UNAMBIGUOUS = frozenset(("PASSED", "FAILED", "ERROR"))


def object_without_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=object_without_duplicate_keys)


def audit(gold, status_map):
    if not isinstance(gold, dict) or not isinstance(status_map, dict):
        raise ValueError("gold and statuses must be JSON objects")
    if any(not isinstance(key, str) or not key or not isinstance(value, str)
           for key, value in status_map.items()):
        raise ValueError("status names and values must be strings")

    groups = {}
    seen = set()
    for name in TEST_GROUPS:
        tests = gold.get(name)
        if not isinstance(tests, list) or any(not isinstance(test, str) or not test for test in tests):
            raise ValueError(f"{name} must be an array of nonempty test names")
        if len(tests) != len(set(tests)) or seen.intersection(tests):
            raise ValueError("duplicate expected test identity")
        seen.update(tests)
        groups[name] = tests

    details = {}
    reasons = []
    for name in TEST_GROUPS:
        tests = groups[name]
        rows = []
        for test in tests:
            status = status_map.get(test)
            classification = (
                "missing" if status is None else
                "passed" if status == "PASSED" else
                "failed" if status in ("FAILED", "ERROR") else
                "unscorable"
            )
            rows.append({"test": test, "status": status, "classification": classification})
            if status not in UNAMBIGUOUS:
                reasons.append({"group": name, "test": test, "status": status,
                                "reason": "missing" if status is None else "ambiguous_status"})
        if not tests:
            reasons.append({"group": name, "test": None, "status": None, "reason": "no_coverage"})
        details[name] = {
            "coverage": "observed" if tests else "no_coverage",
            "tests": rows,
            "passed": sum(row["classification"] == "passed" for row in rows),
            "failed": sum(row["classification"] == "failed" for row in rows),
            "unscorable": sum(row["classification"] in ("missing", "unscorable") for row in rows),
        }

    resolved = strict_fix_rate = None
    if not reasons:
        new = details["FAIL_TO_PASS"]
        old = details["PASS_TO_PASS"]
        resolved = new["failed"] == 0 and old["failed"] == 0
        strict_fix_rate = 0.0 if old["failed"] else new["passed"] / len(groups["FAIL_TO_PASS"])
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "unscorable" if reasons else "scorable",
        "groups": details,
        "unscorable_reasons": reasons,
        "extra_parsed_tests": len(set(status_map) - seen),
        "resolved": resolved,
        "strict_fix_rate": strict_fix_rate,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--statuses", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(read_json(args.gold), read_json(args.statuses))
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2))
    except (OSError, UnicodeError, ValueError) as error:
        print(f"check_test_status: {error}", file=sys.stderr)
        return 2
    return 0 if result["status"] == "scorable" else 1


if __name__ == "__main__":
    sys.exit(main())
