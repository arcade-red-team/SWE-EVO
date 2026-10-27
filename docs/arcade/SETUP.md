# SWE-EVO experiment setup

Status: preparation only. No benchmark trajectory or evaluation has been run.
Do not start the full experiment until the owner approves its cost and the
blocking items below are resolved.

Run `python3 scripts/arcade/preflight.py` for read-only preliminary checks.
It checks Codex availability and selected evaluator prerequisites. It exits
nonzero even if its checks pass and is not the experiment runner.
The login status refers only to the current environment and does not establish
that a separate benchmark home is logged in or can access the model.

After obtaining the pinned public JSONL, `python3 scripts/arcade/prepare_dataset.py
PATH_TO_JSONL NEW_PRIVATE_OUTPUT_DIRECTORY` verifies its SHA-256 and creates
48 evaluator records in a new directory outside this checkout. The records
contain gold data. File permissions alone do not isolate processes running as
the same user: the agent's container must not mount or otherwise access this
directory. This preparation does not establish evaluator correctness.

`python3 scripts/arcade/prepare_tasks.py PATH_TO_JSONL NEW_TASK_INPUT_DIRECTORY`
uses the same pinned dataset validation and exports only the instance ID,
repository, base commit and benchmark-provided problem statement. It does not
copy evaluator patch or test fields. The directory must be separately mounted
into the agent environment; file modes alone do not prevent a process running
as the same user from reading evaluator data. This extractor does not establish
isolation or sanitize the benchmark statement.

`python3 scripts/arcade/cohort.py verify --dataset PATH_TO_JSONL --manifest
docs/arcade/cohort.json` verifies that all 48 IDs, repositories and base commits
match the pinned dataset. The committed manifest contains only these identity
fields and has SHA-256
`94c692e79b2d55e85bae65f3a251bded0c68100cf35bba3879a12617cba8386d`.
The `create` action writes a new manifest without evaluator answers. It must
read the private dataset outside the agent environment and does not validate
the images, contracts, trajectories or evaluator outcomes.

`scripts/arcade/prepare_predictions.py --manifest MANIFEST --records PATCHES
--output PREDS_JSON` exports completed Codex patches to the existing evaluator's
SWE-agent `preds.json` shape and refuses missing or duplicate manifest IDs.
An empty patch is a completed no-change prediction, distinct from a missing
trajectory. This adapter has not been tested with the actual evaluator. Because
the evaluator merges the test patch into the submitted patch, its patch-exists
field alone does not prove that an agent produced a nonempty code patch.

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

The user approved **Codex CLI in both arms**, using `gpt-6-luna` with
`model_reasoning_effort="low"` and three independent repetitions per task.
This replaces the previously proposed OpenHands scaffold and relaxes the
fixed-seed and fixed-temperature requirements: repetitions are not seed values,
and neither sampling control is asserted. Codex is a deviation from the
paper's OpenHands/SWE-agent setup; report it explicitly and do not attribute
differences between separate scaffolds to ARCADE. The paper's OpenHands
100-iteration limit is not automatically equivalent to a Codex budget. Define
and validate equal limits for both Codex arms before the experiment.

Record the Codex CLI version, model identifier, reasoning effort, provider,
repetition index, environment and any observable backend version or usage.
Codex CLI supports choosing the model and reasoning effort, but the inspected
CLI exposes no verified seed or temperature controls. OpenAI's
[GPT-6 guidance](https://developers.openai.com/api/docs/guides/latest-model)
instructs API clients to omit temperature when reasoning is not `none`.
Backend identity and run-to-run reproducibility remain unverified.

The user-approved subscription option uses Codex signed in with ChatGPT;
usage is drawn from the plan allowance and additional credits may apply
depending on account settings. Do not use the user's Codex credentials as an
API key or publish them. MCP connectivity, visibility of the task checkout,
a mandatory pre-submit check, and the two-repair limit have **not** been
demonstrated in this evaluation runtime. A configuration field or prompt alone
does not prove enforcement.

In an offline synthetic check, `--ignore-user-config` was not enough to prevent
global `AGENTS.md` discovery; setting `project_doc_max_bytes=0` suppressed the
project marker but not the global marker. A separate clean Codex home needs a
supported authentication path and reviewed instruction context before model
calls. Do not copy host credentials or expose evaluator gold to the agent;
sandbox access and the MCP subprocess need separate canaries.

A macOS-only canary started the pinned ARCADE MCP server inside a Codex
command sandbox with synthetic data and a minimized environment. Parsing the
workspace succeeded; parsing a sibling fake gold directory or a symlink to it
returned no entities and did not reveal the marker. Both denied-path calls
nevertheless returned `isError=false`, so a driver must treat an empty graph
or unverified coverage as unscorable. The canary allowed read access to
`/opt/homebrew` for local Python dependencies and does not prove complete
filesystem isolation, Linux/Docker behavior, authentication safety, or the
actual experiment configuration.
In a second canary, parsing a workspace with one readable Python file and a
symlink to a denied sibling returned a nonempty graph for the readable file
without reporting the denied file. Thus a nonempty graph also does not prove
complete coverage; snapshot identity and independent file/edge coverage checks
are required before trusting a guard decision.

Another synthetic macOS command-sandbox canary denied path and symlink access
to a private sibling and denied local TCP and Unix socket connections. It also
showed that a private file descriptor deliberately inherited from the parent
remained readable, while the same descriptor was unavailable with `pass_fds=()`;
a synthetic file under `/tmp` was readable in the tested profile. Keep gold
and credentials out of shared temporary paths, close unneeded inherited
descriptors, and repeat canaries with the actual launcher and MCP process. This
does not establish complete isolation or keychain protection.
In a follow-up synthetic `codex sandbox` test, explicitly denying `:tmpdir` and
`:slash_tmp` blocked that temporary-file read while retaining workspace access;
an inherited descriptor remained readable. The actual `codex exec` tool loop
and MCP process have not been shown to use this profile.
A separate no-model app-server canary with a synthetic clean Codex home
reported the configured profile on `thread/start`; a standalone `command/exec`
read its workspace marker and was denied a private sibling marker. Two runs
matched. This does not establish that shell or patch tools in an actual model
turn, MCP, credential access or all filesystem paths use the same protections.

`scripts/arcade/guard.py` provides a preliminary decision function for supported
contracts. It compares MCP findings with the frozen baseline and checks edge
rules against the ARCADE conformance source hash at commit
`0c5a2b7dac0baf2c406b48781433dd9463b017b3`. A missing finding or incomplete
coverage is unscorable. The function relies on caller-supplied snapshot hashes,
repair count and coverage evidence: it does not itself bind MCP to the tree,
prove isolation, call Codex, or enforce a submission boundary. The eventual
driver must pin the entire ARCADE runtime, not just this checked source file.
Persistent baseline findings are also unscorable: component-level aggregation
can hide a newly introduced underlying dependency on the same component pair.

`scripts/arcade/recovery_probe.py` examines one clean source checkout at an
explicit base SHA, checks the ARCADE source tree hash, and compares two cold
package recoveries. It records files with entities split across recovered
components and selected files with no entities; it does not create a contract.
For the public Requests base `ca15d4808734c86801c8f3d80c9152c35a163dc3`,
ARCADE `0c5a2b7dac0baf2c406b48781433dd9463b017b3` selected 94 of 106
tracked Python files, assigned 816 entities and 770 edges, and split entities
from six files across components. Eight selected files had no entities;
relation coverage was not reported. Two outputs had matching normalized SHA-256
`6968cd35fa9a8ed6d1f1719b8b3eb768190aa533b48adaef47e85dae82f0f5a4`.
This observation used Python 3.12.11, networkx 3.6.1, tree-sitter 0.25.2 and
tree-sitter-python 0.25.0, with tests excluded. The guard maps by file, so it
cannot exactly express these six split files. This is not a complete coverage
assessment or evidence for the other 47 bases.
The subsequent descriptive scan of all 48 bases is documented in
[RECOVERY.md](RECOVERY.md); it does not produce enforceable contracts.

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
On the inspected host, Docker reported server 28.5.1 and `aarch64`. A minimal
`linux/amd64` Alpine 3.20 container (image ID
`sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc`)
ran with no network and reported `x86_64`. This is an emulation canary, not a
SWE-EVO image, test, benchmark or performance validation. Validate the actual
image, architecture, available storage and worker concurrency on the execution
host, and record image pull, CPU and memory costs. The evaluator labels images
x86_64; do not assume an ARM run is equivalent.

Keep credentials outside the repository and pass them through the environment;
only public benchmark data and approved experiment artifacts may leave the
machine. Inspect the data and logs for secrets and internal information before
publishing a branch or PR. Limit access and network egress for execution of
untrusted benchmark code and pin the provider and approved data destination.

## Reproducibility blockers in the inspected snapshot

- The README's OpenHands command refers to
  `OpenHands/evaluation/benchmarks/swe_bench/scripts/run_infer.sh`, but
  `OpenHands/evaluation/` is absent at this commit. Obtain and pin a compatible
  evaluation scaffold from an authoritative source to reproduce that separate
  OpenHands path. This is not a prerequisite for the approved Codex path;
  the Codex inference adapter and its output-to-evaluator mapping still need
  implementation and single-task validation.
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
- A source-level check found that the vendored grading helper omits `SKIPPED`
  cases from both success and failure lists, while an empty list gives a score
  of 1; it also treats `XFAIL` as passing. An all-skipped FAIL_TO_PASS set can
  make the evaluator's Fix Rate division have a zero denominator. Preserve the
  official output, but independently verify each expected test's parsed status,
  report missing, skipped and expected-failure cases, and do not label them
  as verified ordinary passes. Parser-to-evaluator and container behavior
  remain unverified; see `SWE-bench/swebench/harness/grading.py` and
  `SWE-bench/evaluate_instance.py` at the pinned revision.
  `scripts/arcade/check_test_status.py` is a separate strict audit for an
  explicitly supplied gold test list and parsed status map. It marks missing,
  skipped, XFAIL, other ambiguous statuses and empty test groups unscorable,
  including the one task with no PASS_TO_PASS coverage. Its outputs do not
  replace the official benchmark scores and do not validate log provenance.
- The JSONL contains gold `patch`, `all_patch` and `test_patch` fields. Keep
  gold and evaluator-only fields inaccessible to the coding agent and restrict
  its input to approved task context; audit for other answer leakage before
  launching. One task has an empty `PASS_TO_PASS` list, so no regression
  coverage can be inferred for that instance.
- The earlier OpenHands option has `temperature` and `seed` fields, but its
  `openhands/llm/retry_mixin.py` can change temperature on a no-response retry.
  The approved Codex setup makes no fixed-temperature or fixed-seed claim;
  record repetition identifiers as labels only and do not describe them as
  model seeds. Verify the model and effort actually used by the Codex runtime.
- For each task's exact base commit, reconstruct and freeze the architecture
  contract before either arm runs. A seven-repository inventory is not a
  substitute for contracts keyed to every distinct task base. Verify the
  contract's hash, provenance, parser coverage, and conformance behavior on
  clean and planted-violation controls.
- ARCADE recovers components at entity granularity while its conformance
  mapping uses file globs; entities within one file can map to distinct recovered
  components. Verify faithful mapping against each real base before creating
  enforceable rules. A package layout or absent dependency alone does not prove
  a forbidden dependency; unresolved rules and uncovered code are not passes.
- Owner decision: encode only architecture rules supported by evidence from the
  repository at the task base. A new inter-package dependency is not itself a
  violation merely because it did not exist at baseline. Keep the recovered
  graph for descriptive metrics, record each enforced rule's source and scope,
  and mark a task without supported, representable rules as unscorable for the
  guard comparison rather than manufacturing a violation policy. See
  [RULE_EVIDENCE.md](RULE_EVIDENCE.md) for the scoped review of all 48 bases.

## Benchmark interpretation

A task resolves only when all `FAIL_TO_PASS` and `PASS_TO_PASS` tests pass.
Per-instance strict Fix Rate is the proportion of `FAIL_TO_PASS` tests passing
if every `PASS_TO_PASS` test passes, and zero if any regress; the benchmark
averages instance scores. Keep test execution or parser failures separate from
actual test failures. These measures do not establish architecture quality.
The proposed sequential-release experiment is a separate extension, not the
official protocol. Training-data contamination, parser coverage, only seven
Python libraries and small per-repository sample sizes limit interpretation.

See [EVALUATOR-CONTROLS.md](EVALUATOR-CONTROLS.md) for the separate Requests
gold/empty grading controls and unresolved test-environment failures.
