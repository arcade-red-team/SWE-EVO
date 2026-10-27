# SWE-EVO experiment setup

Status: preparation only. No benchmark trajectory or evaluation has been run.
Do not start the full experiment until the owner approves its cost and the
blocking items below are resolved.

Run `python3 scripts/arcade/preflight.py` for read-only preliminary checks.
It exits nonzero even if those checks pass: it cannot verify all readiness
conditions and is not the requested end-to-end experiment runner.

## Sources and licences

- SWE-EVO source inspected at commit
  [`9b83d5af943ba7a17567336f5b18239f73960219`](https://github.com/SWE-EVO/SWE-EVO/tree/9b83d5af943ba7a17567336f5b18239f73960219).
  The root [LICENSE](../../LICENSE) is MIT; retain the copyright and permission
  notice when distributing copies or substantial portions. Embedded components
  have their own licences: [OpenHands/LICENSE](../../OpenHands/LICENSE) is MIT
  outside `enterprise/`, which has a separate licence; consult the applicable
  licences for the dataset, images, seven repositories and dependencies too.
- Paper: [SWE-EVO, arXiv:2512.18470v6](https://arxiv.org/abs/2512.18470v6),
  22 May 2026; the arXiv page identifies a perpetual non-exclusive distribution
  licence for the paper. This is separate from the source-code licence.
- The paper describes 48 release-transition tasks in seven Python repositories:
  dvc (26), dask (8), requests (4), pydantic (3), modin (3), conan (2), and
  scikit-learn (2). Repository proportions are imbalanced.

## Scaffold and infrastructure

OpenHands with CodeActAgent is the provisional scaffold in both arms: the
benchmark README names it and the vendored source contains MCP configuration,
so it is a candidate for integrating the ARCADE server without changing
scaffolds between arms. The paper uses a limit of 100 OpenHands iterations.
MCP connectivity, visibility of the task checkout, a mandatory pre-submit check,
and the two-repair limit have **not** been demonstrated in this evaluation
runtime. A configuration field alone does not prove enforcement.

The root project specifies Python 3.10+; the vendored OpenHands
`pyproject.toml` specifies Python >=3.12,<3.14. The root README gives
`pip install -e .` and requires a compatible scaffold. Use isolated,
version-locked environments rather than installing into a shared interpreter.
The SWE-EVO evaluator uses Docker, pulls the instance `image` references,
retags images and invokes the SWE-bench harness. Image digests, scaffold and
dependency versions must be pinned and recorded before data collection.

The vendored SWE-bench README recommends x86_64, at least 120 GB free disk,
16 GB RAM and 8 CPU cores for SWE-bench; it calls ARM64 support experimental.
Those are upstream SWE-bench recommendations, **not measured SWE-EVO sizing**.
On the inspected host, Docker reported server 28.5.1 and `aarch64`; no image,
container, benchmark or timing validation was performed. Validate architecture,
available storage and worker concurrency on the actual execution host, and
record image pull, CPU and memory costs. The evaluator labels images x86_64;
do not assume an ARM run is equivalent.

Keep credentials outside the repository and pass them through the environment;
only public benchmark data and approved experiment artifacts may leave the
machine. Inspect the data and logs for secrets and internal information before
publishing a branch or PR. Limit access and network egress for execution of
untrusted benchmark code and pin the provider and approved data destination.

## Reproducibility blockers in the inspected snapshot

- The README's OpenHands command refers to
  `OpenHands/evaluation/benchmarks/swe_bench/scripts/run_infer.sh`, but
  `OpenHands/evaluation/` is absent at this commit. Obtain and pin a compatible
  evaluation scaffold from an authoritative source, then prove a single-task
  inference path. Do not substitute an unpinned current release silently.
- The README points to `hf_out/hf_jsonl`, which is absent. The checked-in
  `hf_out/hf_dataset/test/` contains an Arrow file, but the usual
  `save_to_disk` metadata files are absent. Confirm the authoritative dataset,
  reconstruct a usable format with its exact content and record its hash before
  treating it as 48 validated instances.
- `SWE-bench/evaluate_instance.py` reads `output_final/*.json`, which is absent
  from this commit. Restore or derive the required records from a verified
  dataset, preserve all test metadata, and validate evaluation on a clean
  control and a known failing patch before using aggregate metrics. Missing
  trajectories and infrastructure failures must be recorded explicitly, not
  treated as measured failures or silently omitted.
- OpenHands has `temperature` and `seed` configuration fields, but
  `openhands/llm/retry_mixin.py` can change temperature from 0 to 1 on a
  no-response retry. Fix the model snapshot, temperature and each of three seeds
  across both arms, verify actual provider requests and retry behavior, and
  report if the provider does not honor seed. A seed does not guarantee
  deterministic provider output.
- For each task's exact base commit, reconstruct and freeze the architecture
  contract before either arm runs. A seven-repository inventory is not a
  substitute for contracts keyed to every distinct task base. Verify the
  contract's hash, provenance, parser coverage, and conformance behavior on
  clean and planted-violation controls.

## Benchmark interpretation

A task resolves only when all `FAIL_TO_PASS` and `PASS_TO_PASS` tests pass.
Per-instance strict Fix Rate is the proportion of `FAIL_TO_PASS` tests passing
if every `PASS_TO_PASS` test passes, and zero if any regress; the benchmark
averages instance scores. Keep test execution or parser failures separate from
actual test failures. These measures do not establish architecture quality.
The proposed sequential-release experiment is a separate extension, not the
official protocol. Training-data contamination, parser coverage, only seven
Python libraries and small per-repository sample sizes limit interpretation.
