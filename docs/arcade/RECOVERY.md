# Descriptive recovery baselines

This is source analysis, not an agent trajectory, benchmark result or frozen
architecture contract. The owner chose repository-evidenced rules only: a
dependency missing from a recovered base graph is not a forbidden dependency.
The 48 source commits each need a separately evidenced, representable contract
and coverage validation before either benchmark arm runs.

[`recovery-baselines.jsonl`](recovery-baselines.jsonl) contains one record per
benchmark instance: public repo and base identifiers, the source-content and
normalized graph hashes, file and graph counts, and two measured recovery times.
It contains no prompts, gold patches, private paths or model outcomes. Its
SHA-256 is `0903aa01f471fe5d03c2b2f7557b18087a0aed1226ff282ad742675b6ce2f714`.
The raw full graphs remain local; this file does not redistribute them.

All 48 inputs were matched against the public JSONL pinned in `SETUP.md`; the
source checkouts were checked clean and at their stated Git commits. Each base
was parsed twice without cache and recovered twice in the same process. The two
normalized hashes agreed for every base; the saved graph payloads were then
independently rehashed. This is same-environment repeatability, not independent
process, host or locked-environment reproducibility.

| Repository | Bases | Files split across recovered components, range | Selected Python files without entities, range |
|---|---:|---:|---:|
| Conan | 2 | 135–136 | 49–49 |
| Dask | 8 | 42–44 | 11–12 |
| DVC | 26 | 42–156 | 1–14 |
| Modin | 3 | 3–3 | 111–119 |
| Requests | 4 | 0–6 | 0–8 |
| Pydantic | 3 | 18–18 | 3–3 |
| scikit-learn | 2 | 24–25 | 28–28 |

Of 48 bases, 47 have at least one split file and 47 have at least one selected
file with no entity. No graph reported relation coverage. A file with no entity
is a coverage signal, not proof that its imports were lost. The file-glob guard
cannot exactly express a file whose entities belong to multiple recovered
components. The probe covers Python with tests excluded; in particular it does
not measure Cython `.pyx` or `.pxd` sources. These limitations prevent using
the hashes as proof of complete architecture coverage.

The probe was `scripts/arcade/recovery_probe.py` at source SHA-256
`4eece614660fd4bb3142e0d28f2574b11a30b3616d292f5a87d946b0ea472a9f`,
using ARCADE `0c5a2b7dac0baf2c406b48781433dd9463b017b3` and package source
SHA-256 `b4f6d2f60e558d4d3408989f7af5889d54f91f66f4dddab52ddf7f72226701b3`.
Observed runtime: Python 3.12.11, networkx 3.6.1, tree-sitter 0.25.2 and
tree-sitter-python 0.25.0. Dependency installations were not locked, so these
are observed versions, not a reproducible environment guarantee. See
[`RULE_EVIDENCE.md`](RULE_EVIDENCE.md) for the separately investigated rules.
