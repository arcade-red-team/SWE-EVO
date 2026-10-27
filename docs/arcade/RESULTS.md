# ARCADE-Agent on SWE-EVO: results

**Status: pre-run protocol; no experiment results yet.** Full inference and evaluation require separate approval after the cost estimate. No cells below represent measured outcomes. The protocol and analysis described here still require implementation and validation before the full run.

## Scope and paired comparison

The approved plan compares Codex CLI with `gpt-6-luna` at reasoning effort `low` in both arms: baseline uses no ARCADE guardrail, while arcade uses ARCADE-Agent's MCP server and an enforced conformance check before patch submission, with at most two repairs. This Codex scaffold is a deviation from the original OpenHands/SWE-agent plan and the paper's reported scaffolds. Each arm is planned for all 48 tasks and three independently started repetitions: 288 initial task runs in total. Both arms start each task independently from its benchmark base revision; neither consumes the other arm's patch. Record the base revision, task data, model identifier, reasoning effort, scaffold, repetition label, resource limits, prompts, test environment, observable backend identity and tool versions. The repetition labels identify runs only: Codex seed and temperature are not fixed or verified, and the runs are not deterministic samples.

`scripts/arcade/analyze.py` implements a preliminary analysis of a complete,
explicit task manifest and paired JSONL outcome set; see its `--help` for the
input schema. Its `repetition` labels identify independent runs, not model seeds.
Pass `--dataset PATH_TO_PINNED_JSONL` when analyzing benchmark outcomes to
verify the manifest's 48 IDs, repositories and base commits against the pinned
dataset; the analysis output explicitly records whether this check ran. Without
that option, the analysis only checks the supplied manifest's count and pairing
and must not be reported as verified official coverage. It deliberately refuses
incomplete data, and is not yet connected to the evaluator or a run pipeline.

Contracts must be produced from each task's base revision before inference, frozen and committed with hashes, and checked against the matching task base. A contract or analysis failure is an error, not zero violations or a passing result. Comparisons of violations must identify findings introduced relative to the base, not just subtract aggregate totals. Record changed rules, identity matching and unsupported or unresolved findings explicitly.

The owner chose repository-evidenced rules only: absence of a dependency in the
base does not make a new dependency a violation. Recovered graphs describe the
observed structure; they do not establish the maintainers' intended rules.

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
- **Primary paired test**: designate repetition 1 before inference; compare binary resolve on matched tasks under the two arms with a two-sided exact McNemar test. Report the discordant pair counts, paired rate difference and a 95% confidence interval, with the number of evaluable pairs. Report repetitions 2 and 3 as separate sensitivity analyses; do not treat 144 task-repetition rows as 144 independent tasks. Repetition indices pair runs by task and schedule, not by model randomness.
- **Repeated-run effect**: compute each task's mean paired difference over its three matched repetitions, then report the overall mean and a 95% task-cluster bootstrap interval; resample whole tasks, retaining all their paired repetitions. This is an estimate across the sampled tasks, not proof of a general population effect. Pair continuous outcomes by task and repetition, average paired differences within each task, and use a two-sided paired permutation/sign-flip test across tasks with a 95% task-cluster bootstrap interval. Specify the statistic, number of draws and analysis random seed in the run manifest; this analysis seed is distinct from model sampling. Report effect sizes and denominators, not only p-values. Secondary metrics are exploratory; disclose multiple comparisons and avoid interpreting them as independent confirmatory tests.
- **Failures and missingness**: record infrastructure failure, timeout, invalid patch, grading failure, unsupported analysis and missing token usage as distinct statuses. Do not turn unavailable metrics into zero. Predefine and publish retry and timeout rules before inference, apply them equally, and report all attempted runs and complete-pair counts; complete-case analysis can be biased. Where the official evaluator defines a valid failure as unresolved, preserve its status and score separately from infrastructure errors.
- **Architecture metrics**: report introduced findings, cycles, package-level coupling and instability deltas, and smells only when the parser and metric support are verified for the examined code. Record baseline and patch analysis, included/excluded files, unresolved imports and analysis errors. Define graph direction, aggregation and cycle identity before calculating deltas. Files and added/deleted lines come from the patch. Record elapsed time and, where observable, token usage, subscription quota or credit usage and actual monetary cost, including repair and relevant retries. Report unavailable per-run billing or quota attribution as unavailable, not zero or an estimate derived from API rates.

## Limitations

The benchmark contains 48 release tasks, with 26 from dvc and only two each from conan and scikit-learn; per-repository estimates will be imprecise and do not carry equal weight in the overall task-average result. Repetitions on the same task are correlated, and tasks within a repository may also be related. One-task change in aggregate resolve is approximately 2.08 percentage points per repetition. Generalization beyond these Python library projects is limited. Model alias or backend changes and unavailable seed/temperature controls further limit reproducibility; a repetition label does not establish equivalent randomness between arms.

Public release histories, tests, issues and benchmark data may have appeared in model training. Record the model identifier and backend identity if available; blocking task-container access to future source reduces some leakage but cannot prove absence of training contamination. The independent baseline must not see the frozen contract or arcade feedback. Both arms must receive the same benchmark-provided problem context and equivalent budgets, except for the explicitly studied guardrail and its bounded repairs.

Parser coverage, dynamic imports, generated code, unresolved dependencies and package-boundary inference can hide or misclassify architecture findings. Recovered structure alone does not establish intended layering; inferred rules are hypotheses and their evidence and exceptions need review. A lack of reported findings is not evidence of no architectural change if coverage is missing. Changes in graphs, cycles, coupling or smells are proxies rather than proof of maintainability.

The sequential-release experiment, if performed, is **our optional proposed procedure**, not official SWE-EVO protocol. A later release starts from an agent-modified prior release; its outcomes therefore depend on earlier failures and are not directly comparable to the independent-task primary benchmark. Record the full lineage and analyze it separately.

## Sources

- [SWE-EVO paper, arXiv 2512.18470](https://arxiv.org/html/2512.18470): benchmark definitions, composition, experimental setup and limitations.
- [SWE-EVO README](https://github.com/SWE-EVO/SWE-EVO/blob/9b83d5af943ba7a17567336f5b18239f73960219/README.md): scaffold and evaluator instructions at the inspected revision.
- [OpenAI: Using GPT-6](https://developers.openai.com/api/docs/guides/latest-model): reasoning effort and model parameter constraints.
- [OpenAI: ChatGPT Work and Codex](https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex): subscription and API billing distinction.
