#!/usr/bin/env python3
"""Analyze complete, explicitly paired SWE-EVO JSONL outcomes.

Manifest JSON: {"tasks": [{"id": "...", "repo": "..."}, ...]}.
JSONL: {"task_id": "...", "repetition": 1, "mode": "baseline"|"arcade",
        "status": "measured", "resolved": true|false,
        "metrics": {"metric_name": number, ...}}.
Each task must occur once for every mode and repetition 1, 2 and 3. Missing or
unmeasured outcomes abort analysis instead of being silently excluded.
"""

import argparse
import hashlib
import itertools
import json
import math
import random
import sys
from pathlib import Path

REPETITIONS = (1, 2, 3)
MODES = ("baseline", "arcade")


def object_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(text):
    return json.loads(text, object_pairs_hook=object_no_duplicates,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError(f"invalid JSON number: {value}")))


def load_inputs(manifest_path, outcome_path, metric, expected_tasks):
    manifest_bytes = Path(manifest_path).read_bytes()
    outcome_bytes = Path(outcome_path).read_bytes()
    manifest = read_json(manifest_bytes)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("tasks"), list):
        raise ValueError("manifest must contain a tasks list")
    tasks = {}
    for task in manifest["tasks"]:
        if not isinstance(task, dict) or not isinstance(task.get("id"), str) or not task["id"] or not isinstance(task.get("repo"), str) or not task["repo"]:
            raise ValueError("every manifest task needs nonempty string id and repo")
        if task["repo"] == "all":
            raise ValueError("repository name all is reserved for the aggregate")
        if task["id"] in tasks:
            raise ValueError(f"duplicate task: {task['id']}")
        tasks[task["id"]] = task["repo"]
    if len(tasks) != expected_tasks or expected_tasks < 1:
        raise ValueError(f"expected {expected_tasks} tasks, got {len(tasks)}")
    records = {}
    for number, line in enumerate(outcome_bytes.splitlines(), 1):
        if not line.strip():
            raise ValueError(f"line {number}: blank JSONL line")
        row = read_json(line)
        if not isinstance(row, dict):
            raise ValueError(f"line {number}: expected object")
        task_id, repetition, mode = row.get("task_id"), row.get("repetition"), row.get("mode")
        if not isinstance(task_id, str) or task_id not in tasks or type(repetition) is not int or repetition not in REPETITIONS or mode not in MODES:
            raise ValueError(f"line {number}: unexpected task, repetition or mode")
        key = (task_id, repetition, mode)
        if key in records:
            raise ValueError(f"line {number}: duplicate outcome {key}")
        value = row.get("metrics", {}).get(metric) if isinstance(row.get("metrics"), dict) else None
        if row.get("status") != "measured" or type(row.get("resolved")) is not bool:
            raise ValueError(f"line {number}: outcome is not measured with a boolean resolved")
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError(f"line {number}: metric {metric!r} missing or non-finite")
        records[key] = row
    expected = {(task_id, repetition, mode) for task_id in tasks for repetition in REPETITIONS for mode in MODES}
    missing = expected - records.keys()
    if missing:
        raise ValueError(f"missing {len(missing)} outcomes; first: {sorted(missing)[0]}")
    return tasks, records, hashlib.sha256(manifest_bytes).hexdigest(), hashlib.sha256(outcome_bytes).hexdigest()


def mean(values):
    return math.fsum(values) / len(values)


def exact_mcnemar(before, after):
    if len(before) != len(after) or not before:
        raise ValueError("McNemar requires nonempty matched pairs")
    wins = sum(not b and a for b, a in zip(before, after))
    losses = sum(b and not a for b, a in zip(before, after))
    discordant = wins + losses
    p = min(1.0, 2.0 * sum(math.comb(discordant, i) for i in range(min(wins, losses) + 1)) / (2 ** discordant)) if discordant else 1.0
    return {"baseline_only": losses, "arcade_only": wins, "p_two_sided_exact": p}


def quantile(values, p):
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    low = int(index)
    high = math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def bootstrap(values, draws, rng):
    n = len(values)
    samples = [mean([values[rng.randrange(n)] for _ in range(n)]) for _ in range(draws)]
    return [quantile(samples, 0.025), quantile(samples, 0.975)]


def sign_flip(values, draws, rng):
    # Test the mean paired difference under independent exchangeability of
    # arm labels for each task. Exact enumeration for small samples.
    observed = abs(math.fsum(values))
    tolerance = 1e-12 * max(1.0, observed, math.fsum(map(abs, values)))
    if len(values) <= 16:
        assignments = itertools.product((-1, 1), repeat=len(values))
        total = 1 << len(values)
        extreme = sum(abs(math.fsum(x * s for x, s in zip(values, signs))) >= observed - tolerance for signs in assignments)
        return {"method": "exact sign flip", "assignments": total, "p_two_sided": extreme / total}
    extreme = 0
    for _ in range(draws):
        candidate = abs(math.fsum(x if rng.getrandbits(1) else -x for x in values))
        extreme += candidate >= observed - tolerance
    return {"method": "Monte Carlo sign flip with plus-one correction", "draws": draws, "p_two_sided": (extreme + 1) / (draws + 1)}


def analyze(tasks, records, metric, draws, analysis_seed):
    if draws < 1:
        raise ValueError("draws must be positive")
    rng = random.Random(analysis_seed)
    all_ids = sorted(tasks)
    groups = {"all": all_ids}
    for repo in sorted(set(tasks.values())):
        groups[repo] = [task_id for task_id in all_ids if tasks[task_id] == repo]
    output = {}
    for name, ids in groups.items():
        repetition_results = {}
        for repetition in REPETITIONS:
            before = [records[(task_id, repetition, "baseline")]["resolved"] for task_id in ids]
            after = [records[(task_id, repetition, "arcade")]["resolved"] for task_id in ids]
            differences = [int(a) - int(b) for b, a in zip(before, after)]
            repetition_results[str(repetition)] = {
                "n_pairs": len(ids), "baseline_rate": mean(before), "arcade_rate": mean(after),
                "paired_difference": mean(differences), "difference_95_percentile_bootstrap_ci": bootstrap(differences, draws, rng),
                **exact_mcnemar(before, after),
            }
        binary_diffs = [mean([int(records[(task_id, repetition, "arcade")]["resolved"]) - int(records[(task_id, repetition, "baseline")]["resolved"]) for repetition in REPETITIONS]) for task_id in ids]
        continuous_diffs = [mean([records[(task_id, repetition, "arcade")]["metrics"][metric] - records[(task_id, repetition, "baseline")]["metrics"][metric] for repetition in REPETITIONS]) for task_id in ids]
        baseline_metric = mean([records[(task_id, repetition, "baseline")]["metrics"][metric] for task_id in ids for repetition in REPETITIONS])
        arcade_metric = mean([records[(task_id, repetition, "arcade")]["metrics"][metric] for task_id in ids for repetition in REPETITIONS])
        output[name] = {
            "n_tasks": len(ids), "primary_repetition": 1, "resolve_by_repetition": repetition_results,
            "resolve_three_repetition_mean_paired_difference": mean(binary_diffs),
            "resolve_three_repetition_difference_95_percentile_bootstrap_ci": bootstrap(binary_diffs, draws, rng),
            "continuous_metric": {"name": metric, "baseline_mean": baseline_metric, "arcade_mean": arcade_metric,
                "mean_paired_difference": mean(continuous_diffs),
                "difference_95_percentile_bootstrap_ci": bootstrap(continuous_diffs, draws, rng),
                "paired_sign_flip": sign_flip(continuous_diffs, draws, rng)},
        }
    return {"analysis_seed": analysis_seed, "bootstrap_draws": draws, "repetitions": list(REPETITIONS), "groups": output}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="JSON task ID and repository manifest")
    parser.add_argument("--outcomes", required=True, help="JSONL per task, repetition, and arm")
    parser.add_argument("--metric", required=True, help="one numeric metric to compare")
    parser.add_argument("--expected-tasks", type=int, default=48)
    parser.add_argument("--dataset", help="pinned evaluator-only JSONL to verify task IDs, repos and base commits")
    parser.add_argument("--draws", type=int, default=10000)
    parser.add_argument("--analysis-seed", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        verified_hash = None
        if args.dataset:
            import cohort
            verified_hash = cohort.verify(args.manifest, Path(args.dataset))
        tasks, records, manifest_hash, outcomes_hash = load_inputs(args.manifest, args.outcomes, args.metric, args.expected_tasks)
        if verified_hash is not None and verified_hash != manifest_hash:
            raise ValueError("manifest changed after cohort verification")
        result = analyze(tasks, records, args.metric, args.draws, args.analysis_seed)
        result["input_sha256"] = {"manifest": manifest_hash, "outcomes": outcomes_hash}
        result["cohort_verified_against_pinned_dataset"] = verified_hash is not None
        print(json.dumps(result, allow_nan=False, sort_keys=True, indent=2))
    except (ValueError, OSError, UnicodeError, OverflowError) as exc:
        print(f"analysis error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
