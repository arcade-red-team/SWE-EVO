"""Clean and adversarial tests for fail-closed conformance decisions."""

import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[2] / "scripts/arcade/guard.py"
spec = importlib.util.spec_from_file_location("arcade_guard", SCRIPT)
assert spec and spec.loader
guard = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = guard
spec.loader.exec_module(guard)

CONTRACT = json.dumps({"components": [{"name": "api", "match": "api/**"}, {"name": "service", "match": "service/**"}, {"name": "store", "match": "store/**"}], "forbid": [{"from": "api", "to": "store"}], "budgets": {"no_cycles": True}}).encode()
DIGEST = hashlib.sha256(CONTRACT).hexdigest()
BASE = guard.Binding("a" * 64, "a" * 64, "a" * 64, DIGEST, DIGEST, DIGEST, True)
CANDIDATE = guard.Binding("b" * 64, "b" * 64, "b" * 64, DIGEST, DIGEST, DIGEST, True)
CLEAN = {"verdict": "PASS", "errors": 0, "warnings": 0, "violations": [],
         "component_edges": [{"from": "api", "to": "service", "count": 2}],
         "component_sizes": {"api": 1, "service": 1, "store": 1}, "num_entities": 3,
         "unmapped_entities": 0, "budgets_not_evaluated": []}


def result_forbidden():
    result = copy.deepcopy(CLEAN)
    result["verdict"] = "FAIL"
    result["errors"] = 1
    result["component_edges"].append({"from": "api", "to": "store", "count": 1})
    result["violations"] = [{"id": "forbidden-dependency:0", "rule": "forbidden-dependency", "severity": "error", "from": "api", "to": "store", "message": "forbidden", "fix": "remove"}]
    return result


class GuardTest(unittest.TestCase):
    def decide(self, base, candidate, repairs=0, binding=CANDIDATE, contract=CONTRACT):
        return guard.decide(base, candidate, contract, BASE, binding, repairs)

    def test_clean_and_planted_violation_with_two_repairs(self):
        self.assertEqual(self.decide(CLEAN, CLEAN).status, "accept")
        result = result_forbidden()
        for repairs in (0, 1):
            decision = self.decide(CLEAN, result, repairs)
            self.assertEqual(decision.status, "repair")
            self.assertEqual(decision.new_violations, (("forbidden-dependency", "api", "store"),))
        self.assertEqual(self.decide(CLEAN, result, 2).status, "repair_limit_reached")
        self.assertEqual(self.decide(CLEAN, result, 3).status, "unscorable")

    def test_new_dependency_is_not_a_violation_without_a_rule(self):
        candidate = copy.deepcopy(CLEAN)
        candidate["component_edges"].append({"from": "service", "to": "store", "count": 1})
        decision = self.decide(CLEAN, candidate)
        self.assertEqual(decision.status, "accept")
        self.assertEqual(decision.new_violations, ())

    def test_contract_without_supported_rules_is_unscorable(self):
        contract = json.dumps({"components": [{"name": "api", "match": "api/**"}]}).encode()
        digest = hashlib.sha256(contract).hexdigest()
        base = guard.Binding("a" * 64, "a" * 64, "a" * 64, digest, digest, digest, True)
        candidate = guard.Binding("b" * 64, "b" * 64, "b" * 64, digest, digest, digest, True)
        decision = guard.decide(CLEAN, CLEAN, contract, base, candidate, 0)
        self.assertEqual(decision.status, "unscorable")

    def test_finding_identity_is_not_numbered_mcp_id(self):
        baseline = result_forbidden()
        candidate = copy.deepcopy(baseline)
        candidate["violations"][0]["id"] = "forbidden-dependency:57"
        self.assertEqual(self.decide(baseline, candidate).status, "unscorable")
        candidate["component_edges"][-1]["count"] += 1
        self.assertEqual(self.decide(baseline, candidate).status, "unscorable")
        candidate["violations"].append(copy.deepcopy(candidate["violations"][0]))
        candidate["errors"] = 2
        self.assertEqual(self.decide(baseline, candidate).status, "unscorable")
        self.assertEqual(self.decide(baseline, CLEAN).status, "accept")

    def test_suppressed_forbidden_finding_fails_closed(self):
        candidate = result_forbidden()
        candidate.update(verdict="PASS", errors=0, violations=[])
        self.assertEqual(self.decide(CLEAN, candidate).status, "unscorable")

    def test_missing_schema_error_unmapped_and_budget_fail_closed(self):
        examples = [{"error": "missing spec"}, {}, {"verdict": "PASS"}]
        for key, value in (("unmapped_entities", 1), ("budgets_not_evaluated", ["max_new_smells"]), ("component_sizes", {}), ("verdict", "PASS")):
            example = result_forbidden() if key == "verdict" else copy.deepcopy(CLEAN)
            example[key] = value
            examples.append(example)
        for example in examples:
            with self.subTest(example=example):
                self.assertEqual(self.decide(CLEAN, example).status, "unscorable")

    def test_hash_mismatch_or_unsupported_budget_fail_closed(self):
        wrong = guard.Binding("b" * 64, "b" * 64, "c" * 64, DIGEST, DIGEST, DIGEST, True)
        self.assertEqual(self.decide(CLEAN, CLEAN, binding=wrong).status, "unscorable")
        uncovered = guard.Binding("b" * 64, "b" * 64, "b" * 64, DIGEST, DIGEST, DIGEST, False)
        self.assertEqual(self.decide(CLEAN, CLEAN, binding=uncovered).status, "unscorable")
        self.assertEqual(self.decide(CLEAN, CLEAN, contract=b"{}").status, "unscorable")
        with patch.object(guard, "_CONFORMANCE_SHA256", "0" * 64):
            self.assertEqual(self.decide(CLEAN, CLEAN).status, "unscorable")
        budget = json.dumps({"components": [{"name": "api", "match": "api/**"}], "forbid": [], "budgets": {"min_turbomq": 1}}).encode()
        digest = hashlib.sha256(budget).hexdigest()
        base = guard.Binding("a" * 64, "a" * 64, "a" * 64, digest, digest, digest, True)
        candidate = guard.Binding("b" * 64, "b" * 64, "b" * 64, digest, digest, digest, True)
        self.assertEqual(guard.decide(CLEAN, CLEAN, budget, base, candidate, 0).status, "unscorable")

    def test_cycles_use_component_members_not_ordinal_ids(self):
        candidate = copy.deepcopy(CLEAN)
        candidate["component_edges"].append({"from": "service", "to": "api", "count": 1})
        candidate["verdict"] = "FAIL"
        candidate["errors"] = 1
        candidate["violations"] = [{"id": "dependency-cycle:0", "rule": "dependency-cycle", "severity": "error", "message": "cycle", "fix": "break"}]
        decision = self.decide(CLEAN, candidate)
        self.assertEqual(decision.new_violations, (("dependency-cycle", "api", "service"),))
        candidate["violations"] = []
        candidate["errors"] = 0
        candidate["verdict"] = "PASS"
        self.assertEqual(self.decide(CLEAN, candidate).status, "unscorable")

    def test_invalid_contract_rules_and_unknown_fields_fail_closed(self):
        cases = [
            {"unknown_guard_rule": True},
            {"allow": [{"from": "missing", "to": "store"}]},
            {"layers": ["application"], "components": [{"name": "api", "match": "api/**", "layer": "missing"}]},
        ]
        for change in cases:
            spec = json.loads(CONTRACT)
            spec.update(change)
            data = json.dumps(spec).encode()
            digest = hashlib.sha256(data).hexdigest()
            base = guard.Binding("a" * 64, "a" * 64, "a" * 64, digest, digest, digest, True)
            candidate = guard.Binding("b" * 64, "b" * 64, "b" * 64, digest, digest, digest, True)
            with self.subTest(change=change):
                self.assertEqual(guard.decide(CLEAN, CLEAN, data, base, candidate, 0).status, "unscorable")

    def test_layer_rule_and_allow_override_match_pinned_semantics(self):
        spec = json.loads(CONTRACT)
        spec["layers"] = ["upper", "lower"]
        spec["components"][0]["layer"] = "upper"
        spec["components"][1]["layer"] = "lower"
        spec["components"][2]["layer"] = "lower"
        candidate_result = copy.deepcopy(CLEAN)
        candidate_result["component_edges"] = [{"from": "service", "to": "api", "count": 1}]
        candidate_result["violations"] = [{"id": "layer-violation:0", "rule": "layer-violation", "severity": "error", "message": "layer", "fix": "invert", "from": "service", "to": "api"}]
        candidate_result["errors"] = 1
        candidate_result["verdict"] = "FAIL"
        def check(data, result):
            encoded = json.dumps(data).encode()
            digest = hashlib.sha256(encoded).hexdigest()
            base = guard.Binding("a" * 64, "a" * 64, "a" * 64, digest, digest, digest, True)
            candidate = guard.Binding("b" * 64, "b" * 64, "b" * 64, digest, digest, digest, True)
            return guard.decide(CLEAN, result, encoded, base, candidate, 0)
        self.assertEqual(check(spec, candidate_result).status, "repair")
        suppressed = copy.deepcopy(candidate_result)
        suppressed.update(violations=[], errors=0, verdict="PASS")
        self.assertEqual(check(spec, suppressed).status, "unscorable")
        spec["allow"] = [{"from": "lower", "to": "upper"}]
        self.assertEqual(check(spec, suppressed).status, "accept")


if __name__ == "__main__":
    unittest.main()
