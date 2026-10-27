# SWE-EVO experiment setup

Status: preparation only. No benchmark trajectory or evaluation has been run.
Do not start the full experiment until the owner approves its cost and the
blocking items below are resolved.

Run `python3 scripts/arcade/preflight.py` for read-only preliminary checks.
It exits nonzero even if those checks pass: it cannot verify all readiness
conditions and is not the requested end-to-end experiment runner.

After obtaining the pinned public JSONL, `python3 scripts/arcade/prepare_dataset.py
PATH_TO_JSONL NEW_PRIVATE_OUTPUT_DIRECTORY` verifies its SHA-256 and creates
48 evaluator records in a new directory outside this checkout. The records
contain gold data. File permissions alone do not isolate processes running as
the same user: the agent's container must not mount or otherwise access this
directory. This preparation does not establish evaluator correctness.

## Sources and licences

- SWE-EVO source inspected at commit
  [`9b83d5af943ba7a17567336f5b18239f73960219`](https://github.com/SWE-EVO/SWE-EVO/tree/9b83d5af943ba7a17567336f5b18239f73960219).
  The root [LICENSE](../../LICENSE) is MIT; retain the copyright and permission
  notice when distributing copies or substantial portions. The pinned Hugging
  Face dataset card declares `apache-2.0` in its metadata but says MIT in its
  prose: this conflict is unresolved and needs clarification before redistribution.
  Embedded components have their own licences: [OpenHands/LICENSE](../../OpenHands/LICENSE) is MIT
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
  Candidate source: [OpenHands 0.58.0 at `acc427e15f4f2bdd5bf6ceed368888f3379f88a5`](https://github.com/OpenHands/OpenHands/tree/acc427e15f4f2bdd5bf6ceed368888f3379f88a5/evaluation).
  The vendored version number, `pyproject.toml` and `poetry.lock` match this
  tag, as do the inspected CodeActAgent and controller files. However, 17
  tracked Python files under `openhands/` differ, including LLM and runtime
  code; the complete source trees do not match. Compatibility and licensing
  of the recovered files must be checked, then the path exercised; this is
  a candidate, not a verified replacement. OpenHands' own licence applies to
  its source, with a separate enterprise licence; retain applicable notices.
- The SWE-EVO README's nine-argument OpenHands example does not match the
  [candidate script's ten-argument interface](https://github.com/OpenHands/OpenHands/blob/acc427e15f4f2bdd5bf6ceed368888f3379f88a5/evaluation/benchmarks/swe_bench/scripts/run_infer.sh):
  `MAX_ITER` is the fifth argument, followed by workers, dataset, split,
  number of runs and mode. Inserting `100` as the fifth argument is necessary
  for this candidate's interface, but does not prove the script works with the
  vendored scaffold or dataset. Its helper can switch Git revisions, so use an
  isolated checkout. The candidate
  [inference adapter explicitly disables MCP](https://github.com/OpenHands/OpenHands/blob/acc427e15f4f2bdd5bf6ceed368888f3379f88a5/evaluation/benchmarks/swe_bench/run_infer.py#L254-L263);
  enabling MCP and an enforced finish/check/repair hook require implementation
  and runtime verification. Merely adding MCP configuration is insufficient.
- The README points to `hf_out/hf_jsonl`, which is absent from the GitHub
  snapshot. The public [Hugging Face dataset](https://huggingface.co/datasets/Fsoft-AIC/SWE-EVO/tree/77310c70d3648d6815f6a7555ecc492bc28c44ec)
  at revision `77310c70d3648d6815f6a7555ecc492bc28c44ec` contains
  `SWE-EVO/hf_jsonl/test.jsonl` (SHA-256
  `a5dc7fccf7d839140e2005b09937e0f83910a61518027ef72d42134542246f87`)
  and a complete `SWE-EVO/hf_dataset/` metadata tree. The JSONL inspection
  found 48 unique path-safe instance IDs and 48 distinct repository/base-commit
  pairs. All base commits have the shape of a full Git SHA; this is not proof
  that those commits, images, test metadata or task contents are correct.
  The pinned Hugging Face Arrow SHA-256
  `9e571749b6d1e52526b0ecbe078594a6d2522333e39f5463105868ebef5346ba`
  differs from the checked-in GitHub Arrow SHA-256
  `74e7c63160ada4ceba71d5d89a9bb7c9794f4574b384458d546eb65cdb730520`;
  do not mix the two snapshots without validating their contents.
- `SWE-bench/evaluate_instance.py` reads `output_final/*.json`, which is absent
  from the GitHub commit. The pinned JSONL has the fields needed to attempt
  one-to-one derivation of these records. Validate schema, unique safe IDs,
  repo/base identity, image digests, test patch and test lists, and the
  evaluator's repo/version mappings. The source inspection does not prove
  that reconstruction or evaluation works. Validate the actual evaluator on a
  clean control and a known failing patch before using aggregate metrics.
  Missing trajectories and infrastructure failures must be recorded explicitly,
  not treated as measured failures or silently omitted.
- The JSONL contains gold `patch`, `all_patch` and `test_patch` fields. Keep
  gold and evaluator-only fields inaccessible to the coding agent and restrict
  its input to approved task context; audit for other answer leakage before
  launching. One task has an empty `PASS_TO_PASS` list, so no regression
  coverage can be inferred for that instance.
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
