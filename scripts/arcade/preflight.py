#!/usr/bin/env python3
"""Read-only preliminary checks for the Codex SWE-EVO experiment."""

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE_COMMIT = "9b83d5af943ba7a17567336f5b18239f73960219"
EXPECTED_INSTANCES = 48


def command(args: list[str], root: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            args, cwd=root, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    return result.returncode == 0, (result.stdout or result.stderr).strip()


def check(root: Path, inputs: Path | None = None) -> list[tuple[str, bool, str]]:
    results = []
    codex_ok, version = command(["codex", "--version"], root)
    results.append(("Codex CLI installed", codex_ok, version if codex_ok else "unavailable"))
    login_ok, login = command(["codex", "login", "status"], root)
    results.append(("Codex ChatGPT login", login_ok and "Logged in using ChatGPT" in login,
                    "ChatGPT login detected" if login_ok and "Logged in using ChatGPT" in login
                    else "not verified"))

    evaluator = root / "SWE-bench/evaluate_instance.py"
    results.append(("SWE-EVO evaluator", evaluator.is_file(), str(evaluator)))
    files = sorted(inputs.glob("*.json")) if inputs and inputs.is_dir() else []
    ids = set()
    invalid = 0
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            instance_id = data.get("instance_id")
            if not isinstance(instance_id, str) or not instance_id:
                raise ValueError("missing instance_id")
            ids.add(instance_id)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError, AttributeError):
            invalid += 1
    inputs_ok = len(files) == EXPECTED_INSTANCES and len(ids) == EXPECTED_INSTANCES and not invalid
    results.append((
        "Evaluator instance JSON count and unique IDs", inputs_ok,
        f"{inputs or 'not provided'}: {len(files)} files, {len(ids)} unique IDs, {invalid} invalid; "
        f"expected {EXPECTED_INSTANCES}",
    ))

    base_ok, _ = command(["git", "merge-base", "--is-ancestor", BASE_COMMIT, "HEAD"], root)
    results.append(("Pinned SWE-EVO base ancestor", base_ok, BASE_COMMIT))

    docker_ok, platform = command(
        ["docker", "version", "--format", "{{.Server.Os}}/{{.Server.Arch}}"], root
    )
    # Images in the benchmark are x86-64. An ARM daemon may emulate them, but
    # this read-only check cannot establish that emulation actually works.
    platform_ok = docker_ok and platform == "linux/amd64"
    results.append(("Docker server (native linux/amd64)", platform_ok, platform or "unavailable"))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluator-inputs", type=Path,
                        help="evaluator-only directory, inaccessible to the agent")
    args = parser.parse_args()
    results = check(ROOT, args.evaluator_inputs)
    for label, passed, detail in results:
        print(f"{'PASS' if passed else 'MISSING/UNVERIFIED'} {label}: {detail}")
    print("NOT VERIFIED: authoritative instance identities and fields, guard integration, "
          "frozen contracts, isolation, image contents, model access, runtime "
          "and evaluator end-to-end. This preflight cannot establish readiness.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
