"""Fail-closed decisions over pinned ARCADE MCP conformance results.

This module does not invoke MCP or prove that MCP analyzed a particular tree.
The caller must independently bind actual immutable input snapshots to the
supplied SHA-256 values. Contract bytes are hashed here.
"""

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_EDGE_RULES = frozenset(("forbidden-dependency", "layer-violation"))
_MAX_REPAIRS = 2
_CONFORMANCE_SHA256 = "28669dddd806d4ec10c704e80bba27aa529ff12341f124ff6dd19fb9a3dfb6a4"


@dataclass(frozen=True)
class Binding:
    """Evidence supplied by the caller before and after the MCP check.

    ``coverage_complete`` must only be set from independent coverage evidence;
    the MCP conformance result alone does not prove parser coverage.
    """

    expected_snapshot: str
    checked_snapshot: str
    postcheck_snapshot: str
    expected_contract: str
    checked_contract: str
    postcheck_contract: str
    coverage_complete: bool


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    new_violations: tuple[tuple[str, ...], ...] = ()


def _validate_binding(binding: Binding) -> None:
    values = (binding.expected_snapshot, binding.checked_snapshot, binding.postcheck_snapshot,
              binding.expected_contract, binding.checked_contract, binding.postcheck_contract)
    if any(not isinstance(value, str) or not _SHA256.fullmatch(value) for value in values):
        raise ValueError("invalid snapshot or contract digest")
    if binding.expected_snapshot != binding.checked_snapshot or binding.expected_snapshot != binding.postcheck_snapshot:
        raise ValueError("snapshot does not match checked snapshot")
    if binding.expected_contract != binding.checked_contract or binding.expected_contract != binding.postcheck_contract:
        raise ValueError("contract does not match checked contract")
    if binding.coverage_complete is not True:
        raise ValueError("parser coverage has not been independently verified")


def _cycles(edges: set[tuple[str, str]]) -> list[tuple[str, ...]]:
    """Return sorted strongly connected groups of two or more components."""
    nodes = {name for pair in edges for name in pair}
    forward = {node: [] for node in nodes}
    reverse = {node: [] for node in nodes}
    for source, target in edges:
        forward[source].append(target)
        reverse[target].append(source)
    visited: set[str] = set()
    order: list[str] = []
    for root in sorted(nodes):
        if root in visited:
            continue
        visited.add(root)
        stack = [(root, iter(forward[root]))]
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                order.append(node)
                stack.pop()
            elif child not in visited:
                visited.add(child)
                stack.append((child, iter(forward[child])))
    visited.clear()
    groups: list[tuple[str, ...]] = []
    for root in reversed(order):
        if root in visited:
            continue
        group = []
        todo = [root]
        visited.add(root)
        while todo:
            node = todo.pop()
            group.append(node)
            for child in reverse[node]:
                if child not in visited:
                    visited.add(child)
                    todo.append(child)
        if len(group) > 1:
            groups.append(tuple(sorted(group)))
    return sorted(groups)


def _findings(result: Any, spec: Any, semantics: Any) -> Counter[tuple[str, ...]]:
    no_cycles = spec.budgets.get("no_cycles", False)
    component_names = set(spec.component_names())
    if not isinstance(result, dict) or "error" in result:
        raise ValueError("MCP returned an error or invalid result")
    required_counts = ("errors", "warnings", "num_entities", "unmapped_entities")
    if any(type(result.get(key)) is not int or result[key] < 0 for key in required_counts):
        raise ValueError("MCP result has invalid counts")
    if result["num_entities"] == 0 or result["unmapped_entities"] != 0:
        raise ValueError("empty graph or unmapped entities")
    sizes = result.get("component_sizes")
    if not isinstance(sizes, dict) or any(not isinstance(name, str) or name not in component_names or type(count) is not int or count < 0 for name, count in sizes.items()) or sum(sizes.values()) != result["num_entities"]:
        raise ValueError("invalid component coverage")
    if result.get("budgets_not_evaluated") != []:
        raise ValueError("some budgets are unavailable or unverified")
    violations = result.get("violations")
    edge_values = result.get("component_edges")
    if not isinstance(violations, list) or not isinstance(edge_values, list):
        raise ValueError("missing violations or component edges")
    edges: set[tuple[str, str]] = set()
    for edge in edge_values:
        if not isinstance(edge, dict):
            raise ValueError("invalid component edge")
        source, target, count = edge.get("from"), edge.get("to"), edge.get("count")
        if not isinstance(source, str) or source not in sizes or not isinstance(target, str) or target not in sizes or source == target or type(count) is not int or count < 1:
            raise ValueError("invalid component edge fields")
        if (source, target) in edges:
            raise ValueError("duplicate component edge")
        edges.add((source, target))
    found: Counter[tuple[str, ...]] = Counter()
    error_count = 0
    warning_count = 0
    cycle_count = 0
    for violation in violations:
        if not isinstance(violation, dict):
            raise ValueError("invalid violation")
        if any(not isinstance(violation.get(key), str) for key in ("id", "rule", "severity", "message", "fix")):
            raise ValueError("violation fields are missing or invalid")
        rule, severity = violation.get("rule"), violation.get("severity")
        if severity == "error":
            error_count += 1
        elif severity == "warn":
            warning_count += 1
        else:
            raise ValueError("unknown violation severity")
        if rule in _EDGE_RULES:
            source, target = violation.get("from"), violation.get("to")
            if severity != "error" or not isinstance(source, str) or not isinstance(target, str) or (source, target) not in edges:
                raise ValueError("invalid dependency violation")
            found[(rule, source, target)] += 1
        elif rule == "dependency-cycle" and severity == "error":
            cycle_count += 1
        else:
            # Pinned MCP does not provide structured identities for budget findings.
            raise ValueError("violation rule lacks a supported semantic identity")
    if (error_count, warning_count) != (result["errors"], result["warnings"]):
        raise ValueError("violation counts do not match")
    expected_verdict = "FAIL" if error_count else "WARN" if warning_count else "PASS"
    if result.get("verdict") != expected_verdict:
        raise ValueError("verdict does not match violations")
    expected_edges: Counter[tuple[str, ...]] = Counter()
    for source, target in edges:
        for problem in semantics.dependency_problems(spec, source, target):
            expected_edges[(problem.rule, problem.source, problem.target)] += 1
    observed_edges = Counter({key: count for key, count in found.items() if key[0] in _EDGE_RULES})
    if observed_edges != expected_edges:
        raise ValueError("MCP dependency findings do not match contract and edges")
    if no_cycles:
        groups = _cycles(edges)
        if cycle_count != len(groups):
            raise ValueError("cycle findings do not match component graph")
        found.update(("dependency-cycle", *group) for group in groups)
    elif cycle_count:
        raise ValueError("cycle finding is not enabled by the contract")
    return found


def decide(base: Any, candidate: Any, contract: bytes, base_binding: Binding,
           candidate_binding: Binding, repairs_attempted: int) -> Decision:
    """Compare measured findings and limit repair requests to two rounds."""
    try:
        _validate_binding(base_binding)
        _validate_binding(candidate_binding)
        if base_binding.expected_contract != candidate_binding.expected_contract:
            raise ValueError("baseline and candidate contracts differ")
        if not isinstance(contract, bytes) or hashlib.sha256(contract).hexdigest() != base_binding.expected_contract:
            raise ValueError("contract bytes do not match the frozen digest")
        def unique_object(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise ValueError("duplicate contract key")
                obj[key] = value
            return obj
        spec = json.loads(contract, object_pairs_hook=unique_object)
        if not isinstance(spec, dict):
            raise ValueError("invalid contract")
        if set(spec) - {"intent", "components", "layers", "allow", "forbid", "budgets"}:
            raise ValueError("contract contains unsupported fields")
        budgets = spec.get("budgets", {})
        allow = spec.get("allow", [])
        forbid = spec.get("forbid", [])
        layers = spec.get("layers", [])
        components = spec.get("components", [])
        if not isinstance(budgets, dict) or not isinstance(allow, list) or not isinstance(forbid, list) or not isinstance(layers, list):
            raise ValueError("invalid contract rules")
        if not isinstance(components, list) or not components or any(not isinstance(item, dict) or not isinstance(item.get("name"), str) or not item["name"] or not isinstance(item.get("match"), str) or not item["match"] for item in components):
            raise ValueError("contract components must have names and path matches")
        if any(set(item) - {"name", "match", "layer", "keywords"} for item in components):
            raise ValueError("unsupported component fields")
        if any(not isinstance(item, dict) or set(item) - {"from", "to", "why"} or not isinstance(item.get("from"), str) or not item["from"] or not isinstance(item.get("to"), str) or not item["to"] or not isinstance(item.get("why", ""), str) for item in allow + forbid) or any(not isinstance(layer, str) or not layer for layer in layers):
            raise ValueError("invalid contract dependencies or layers")
        if len(set(layers)) != len(layers):
            raise ValueError("duplicate layer names")
        if any(item.get("layer") is not None and item["layer"] not in layers for item in components):
            raise ValueError("component layer is not declared")
        if any(not isinstance(item.get("keywords", []), list) or any(not isinstance(word, str) for word in item.get("keywords", [])) for item in components):
            raise ValueError("invalid component keywords")
        if not isinstance(spec.get("intent", ""), str):
            raise ValueError("invalid contract intent")
        if set(budgets) - {"no_cycles"} or ("no_cycles" in budgets and type(budgets["no_cycles"]) is not bool):
            raise ValueError("contract budget is unsupported")
        if not forbid and not layers and not budgets.get("no_cycles", False):
            raise ValueError("contract has no supported enforcement rule")
        if type(repairs_attempted) is not int or not 0 <= repairs_attempted <= _MAX_REPAIRS:
            raise ValueError("invalid repair count")
        names = {item["name"] for item in components}
        if len(names) != len(components):
            raise ValueError("duplicate contract component names")
        from arcade_agent.algorithms import conformance as semantics

        source = Path(semantics.__file__)
        if hashlib.sha256(source.read_bytes()).hexdigest() != _CONFORMANCE_SHA256:
            raise ValueError("unsupported ARCADE conformance implementation")
        parsed_spec = semantics.ArchitectureSpec.from_dict(spec)
        for rule in allow + forbid:
            for endpoint in (rule["from"], rule["to"]):
                if not any(semantics._matches(parsed_spec, name, endpoint) for name in names):
                    raise ValueError("dependency rule endpoint matches no component")
        before = _findings(base, parsed_spec, semantics)
        after = _findings(candidate, parsed_spec, semantics)
    except (AttributeError, TypeError, ValueError, UnicodeError, OSError, ImportError) as error:
        return Decision("unscorable", str(error))
    introduced = tuple(sorted((after - before).elements()))
    if not introduced:
        return Decision("accept", "no new supported contract violations")
    if repairs_attempted < _MAX_REPAIRS:
        return Decision("repair", "new contract violations", introduced)
    return Decision("repair_limit_reached", "new contract violations remain", introduced)
