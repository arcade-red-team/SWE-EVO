# ARCADE-Agent on SWE-EVO: results

**Status: pre-run protocol; no experiment results yet.** Full inference and evaluation require separate approval after the cost estimate. No cells below represent measured outcomes. The protocol and analysis described here still require implementation and validation before the full run.

## Scope and paired comparison

The planned benchmark compares the original scaffold (baseline) with the same scaffold using ARCADE-Agent's MCP server and a conformance check before patch submission. The arcade arm may repair a nonconforming patch at most twice. Each arm is planned for all 48 tasks and the same three seed values: 288 initial task runs in total. Both arms start each task independently from its benchmark base revision; neither consumes the other arm's patch. The base revision, task data, model and version, temperature, seed, scaffold, resource limits, prompts, test environment and tool versions must be recorded. Seed support must be verified end to end: a recorded seed alone does not establish deterministic model output.

Contracts must be produced from each task's base revision before inference, frozen and committed with hashes, and checked against the matching task base. A contract or analysis failure is an error, not zero violations or a passing result. Comparisons of violations must identify findings introduced relative to the base, not just subtract aggregate totals. Record changed rules, identity matching and unsupported or unresolved findings explicitly.

## Results by repository

`Not run` means no data have been collected. Counts below are planned task counts from the paper, not results. Each task is planned to have three runs in each arm; denominator and incomplete cases must be reported when populated.

| Repository | Tasks | Baseline resolve / Fix Rate | Arcade resolve / Fix Rate | PASS_TO_PASS regressions, baseline / arcade |
|---|---:|---|---|---|
| dvc | 26 | Not run | Not run | Not run |
| dask | 8 | Not run | Not run | Not run |
| requests | 4 | Not run | Not run | Not run |
| pydantic | 3 | Not run | Not run | Not run |
| modin | 3 | Not run | Not run | Not run |
| conan | 2 | Not run | Not run | Not run |
| scikit-learn | 2 | Not run | Not run | Not run |
| **All** | **48** | **Not run** | **Not run** | **Not run** |

| Repository | New contract violations / dependency cycles | Coupling / instability change and architecture smells | Files / lines changed | Tokens / cost / elapsed time |
|---|---|---|---|---|
| dvc | Not run | Not run | Not run | Not run |
| dask | Not run | Not run | Not run | Not run |
| requests | Not run | Not run | Not run | Not run |
| pydantic | Not run | Not run | Not run | Not run |
| modin | Not run | Not run | Not run | Not run |
| conan | Not run | Not run | Not run | Not run |
| scikit-learn | Not run | Not run | Not run | Not run |
| **All** | **Not run** | **Not run** | **Not run** | **Not run** |

Populate both arms and their paired difference, units, denominator, and 95% confidence intervals for each measured metric. Keep baseline, arcade and per-package raw values in the run records; the second table is a placeholder, not a claim that these measurements are available.

## Definitions and analysis plan

- **Resolve**: for an evaluable task run, all benchmark FAIL_TO_PASS and PASS_TO_PASS tests pass under the candidate patch. Report patch-application, grading failures, and missing evaluations separately.
- **Fix Rate**: the proportion of FAIL_TO_PASS tests passing, provided every PASS_TO_PASS test passes; otherwise zero. Compute the benchmark aggregate as the mean of per-task Fix Rates, not the proportion of pooled tests. Also report raw FAIL_TO_PASS progress and the number of regressed PASS_TO_PASS tests independently.
- **Primary paired test**: choose and record the primary seed before inference; compare binary resolve on matched tasks under the two arms with a two-sided exact McNemar test. Report the discordant pair counts, paired rate difference and a 95% confidence interval, with the number of evaluable pairs. Report the other two seeds as separate sensitivity analyses; do not treat 144 task-seed rows as 144 independent tasks.
- **Repeated-seed effect**: compute each task's mean paired difference over its three matched seeds, then report the overall mean and a 95% task-cluster bootstrap interval; resample whole tasks, retaining all their seed pairs. This is an estimate across the sampled tasks, not proof of a general population effect. Pair continuous outcomes by task and seed, average paired differences within each task, and use a two-sided paired permutation/sign-flip test across tasks with a 95% task-cluster bootstrap interval. Specify the statistic, number of draws and analysis seed in the run manifest. Report effect sizes and denominators, not only p-values. Secondary metrics are exploratory; disclose multiple comparisons and avoid interpreting them as independent confirmatory tests.
- **Failures and missingness**: record infrastructure failure, timeout, invalid patch, grading failure, unsupported analysis and missing token usage as distinct statuses. Do not turn unavailable metrics into zero. Predefine and publish retry and timeout rules before inference, apply them equally, and report all attempted runs and complete-pair counts; complete-case analysis can be biased. Where the official evaluator defines a valid failure as unresolved, preserve its status and score separately from infrastructure errors.
- **Architecture metrics**: report introduced findings, cycles, package-level coupling and instability deltas, and smells only when the parser and metric support are verified for the examined code. Record baseline and patch analysis, included/excluded files, unresolved imports and analysis errors. Define graph direction, aggregation and cycle identity before calculating deltas. Files and added/deleted lines come from the patch; token, monetary cost and elapsed time are recorded per run, including repair and relevant retries.

## Limitations

The benchmark contains 48 release tasks, with 26 from dvc and only two each from conan and scikit-learn; per-repository estimates will be imprecise and do not carry equal weight in the overall task-average result. Repeated seeds on the same task are correlated, and tasks within a repository may also be related. One-task change in aggregate resolve is approximately 2.08 percentage points per seed. Generalization beyond these Python library projects is limited.

Public release histories, tests, issues and benchmark data may have appeared in model training; fixing a model version and blocking task-container access to future source reduces some leakage but cannot prove absence of training contamination. The independent baseline must not see the frozen contract or arcade feedback. Both arms must receive the same benchmark-provided problem context and equivalent budgets, except for the explicitly studied guardrail and its bounded repairs.

Parser coverage, dynamic imports, generated code, unresolved dependencies and package-boundary inference can hide or misclassify architecture findings. Recovered structure alone does not establish intended layering; inferred rules are hypotheses and their evidence and exceptions need review. A lack of reported findings is not evidence of no architectural change if coverage is missing. Changes in graphs, cycles, coupling or smells are proxies rather than proof of maintainability.

The sequential-release experiment, if performed, is **our optional proposed procedure**, not official SWE-EVO protocol. A later release starts from an agent-modified prior release; its outcomes therefore depend on earlier failures and are not directly comparable to the independent-task primary benchmark. Record the full lineage and analyze it separately.

## Sources

- [SWE-EVO paper, arXiv 2512.18470](https://arxiv.org/html/2512.18470): benchmark definitions, composition, experimental setup and limitations.
- [SWE-EVO README](https://github.com/SWE-EVO/SWE-EVO/blob/9b83d5af943ba7a17567336f5b18239f73960219/README.md): scaffold and evaluator instructions at the inspected revision.
