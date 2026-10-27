#!/usr/bin/env python3
"""Inspect one clean Git base with the pinned ARCADE package; no contract is generated."""

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from dataclasses import asdict

sys.dont_write_bytecode = True
ARCADE_COMMIT = "0c5a2b7dac0baf2c406b48781433dd9463b017b3"
ARCADE_SOURCE_SHA256 = "b4f6d2f60e558d4d3408989f7af5889d54f91f66f4dddab52ddf7f72226701b3"
ARCADE_SOURCE_FILES = 80


def git(root: Path, *args: str) -> str:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.check_output(["git", *args], cwd=root, env=env, text=True, stderr=subprocess.PIPE).strip()


def verify_checkout(root: Path, expected: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError("expected base must be a full lowercase 40-character Git SHA")
    if Path(git(root, "rev-parse", "--show-toplevel")).resolve() != root.resolve():
        raise ValueError("checkout must be the repository root")
    if git(root, "rev-parse", "HEAD") != expected:
        raise ValueError("checkout HEAD does not equal the expected base")
    if git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("checkout contains tracked or untracked changes")


def verify_arcade() -> dict:
    package = importlib.import_module("arcade_agent")
    root = Path(package.__file__).resolve().parent
    files = sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    digest = hashlib.sha256()
    for file in files:
        digest.update(file.relative_to(root).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(file.read_bytes()).digest())
    actual = digest.hexdigest()
    if len(files) != ARCADE_SOURCE_FILES or actual != ARCADE_SOURCE_SHA256:
        raise ValueError("loaded ARCADE source tree does not match the pinned source digest")
    versions = {}
    for name in ("tree-sitter", "tree-sitter-python", "networkx"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {"commit": ARCADE_COMMIT, "source_tree_sha256": actual,
            "source_files": len(files), "dependencies": versions,
            "limitations": "source tree verified; interpreter and installed dependencies are not pinned"}


def file_membership(graph, architecture) -> dict[str, list[str]]:
    owner = {}
    for component in architecture.components:
        for entity in component.entities:
            if entity in owner or entity not in graph.entities:
                raise ValueError("recovery returned duplicate or unknown entity")
            owner[entity] = component.name
    if set(owner) != set(graph.entities):
        raise ValueError("recovery did not assign every entity")
    files: dict[str, set[str]] = {}
    for entity_id, entity in graph.entities.items():
        files.setdefault(entity.file_path, set()).add(owner[entity_id])
    return {name: sorted(components) for name, components in sorted(files.items())}


def source_digest(root: Path, files: list[str]) -> str:
    digest = hashlib.sha256()
    for name in files:
        path = root / name
        if path.is_symlink() or not path.resolve(strict=True).is_relative_to(root):
            raise ValueError("selected source contains a symlink or leaves the checkout")
        digest.update(name.encode() + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def probe(root: Path, expected: str) -> dict:
    verify_checkout(root, expected)
    arcade = verify_arcade()
    from arcade_agent.source.parse import _discover_files
    from arcade_agent.tools.parse import parse
    from arcade_agent.tools.recover import recover

    tracked = sorted(git(root, "ls-files", "--", "*.py").splitlines())
    selected = sorted(p.relative_to(root).as_posix() for p in _discover_files(root, ["python"], True, ()))
    if not selected or set(selected) - set(tracked):
        raise ValueError("selected Python files are empty or include untracked or ignored files")
    expected_sources = source_digest(root, selected)

    def measure():
        started = time.monotonic()
        graph = parse(str(root), language="python", use_cache=False, exclude_tests=True)
        architecture = recover(graph, algorithm="pkg")
        elapsed = time.monotonic() - started
        membership = file_membership(graph, architecture)
        data = {
            "base_sha": expected, "arcade": arcade,
            "selected_source_sha256": expected_sources,
            "options": {"language": "python", "use_cache": False, "exclude_tests": True, "algorithm": "pkg"},
            "tracked_python_files": len(tracked), "selected_python_files": len(selected),
            "excluded_python_files": sorted(set(tracked) - set(selected)),
            "entity_source_files": len(membership), "selected_without_entities": sorted(set(selected) - set(membership)),
            "num_entities": graph.num_entities, "num_edges": graph.num_edges,
            "relation_coverage": graph.relation_coverage(), "metadata": graph.metadata,
            "split_files": {name: owners for name, owners in membership.items() if len(owners) > 1},
            "entities": {name: asdict(entity) for name, entity in sorted(graph.entities.items())},
            "edges": sorted((edge.source, edge.target, edge.relation) for edge in graph.edges),
            "components": {component.name: sorted(component.entities) for component in architecture.components},
            "rationale": architecture.rationale,
            "coverage_note": "selected files without entities and undeclared relations are not proof of complete parser coverage",
        }
        payload = json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        return data, hashlib.sha256(payload).hexdigest(), elapsed

    first, first_hash, first_time = measure()
    verify_checkout(root, expected)
    if source_digest(root, selected) != expected_sources:
        raise ValueError("source files changed during recovery")
    second, second_hash, second_time = measure()
    verify_checkout(root, expected)
    if source_digest(root, selected) != expected_sources:
        raise ValueError("source files changed during recovery")
    if first_hash != second_hash:
        raise ValueError("two cold recovery outputs differ")
    return {"data": first, "hashes": [first_hash, second_hash], "seconds": [first_time, second_time]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--output", type=Path, help="new evidence file outside the checkout; stdout if omitted")
    args = parser.parse_args(argv)
    try:
        root = args.checkout.resolve(strict=True)
        if args.output is not None:
            output = args.output.parent.resolve(strict=True) / args.output.name
            if output == root or root in output.parents or output.exists() or output.is_symlink():
                raise ValueError("output must be a new file outside the checkout")
        result = probe(root, args.base_sha)
        text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output is None:
            print(text, end="")
        else:
            with output.open("x", encoding="utf-8") as file:
                file.write(text)
    except (ValueError, OSError, ImportError, subprocess.CalledProcessError) as error:
        print(f"recovery probe error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
