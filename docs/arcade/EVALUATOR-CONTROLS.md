# Evaluator controls: Requests

These are grader controls using the public gold patch and an empty patch, not
agent trajectories or an ARCADE comparison. No model was called. The full logs
and patches are retained locally outside this repository because they contain
gold data. The six-line [`evaluator-control-summary.jsonl`](evaluator-control-summary.jsonl)
contains only aggregate test counts, hashes, timing and public identifiers;
its SHA-256 is `da4287eead4b5c4b4ca13871baf204bba736f0c33a758e81a65311cfee5dfceb`.

The task is `psf__requests_v2.12.2_v2.12.3`, base
`ca15d4808734c86801c8f3d80c9152c35a163dc3`, using the dataset SHA-256
`a5dc7fccf7d839140e2005b09937e0f83910a61518027ef72d42134542246f87`
and `linux/amd64` image digest
`sha256:41767104d2506d564071a2ebf41e74f5c664dc155d75a90e91fa1d3d78aad534`.
The image checkout was verified at the base SHA. The benchmark test patch was
applied for every case. The gold and empty code patches are separate controls.

| Condition | Code patch | FAIL_TO_PASS passed | PASS_TO_PASS passed | Grader reports resolved |
|---|---|---:|---:|---|
| Network disabled | Gold | 4/4 | 107/109 | No |
| Network disabled | Empty | 0/4 | 107/109 | No |
| Isolated dummy-route tarpit | Gold | 4/4 | 109/109 | Yes |
| Isolated dummy-route tarpit | Empty | 0/4 | 109/109 | No |
| Userland timeout mock | Gold | 4/4 | 109/109 | Yes |
| Userland timeout mock | Empty | 0/4 | 109/109 | No |

With network disabled and no route, two old timeout tests received
`NetworkUnreachable` rather than the expected connection timeout. For the
dummy-route diagnostic, a Docker container had no network attachment or host
mount and was not privileged. A temporary `NET_ADMIN` capability configured a
dummy interface and a single host route to `10.255.255.1`; the test process
then dropped its capabilities before `/eval.sh`. A canary observed a socket
timeout, and the test log reported `CapEff=0`, `CapPrm=0`, `NoNewPrivs=1`.
The container's initial process retained its creation-time capability; this
diagnostic does not prove isolation for an untrusted agent or patch.
The mock diagnostic instead intercepted the timeout at user level. Both are
explicit environment modifications, not an unmodified benchmark run.

Every case also reported 134 setup errors outside the 113 listed target tests:
131 recursive `httpbin` fixture errors, two `httpbin_secure` fixture errors,
and one missing `mocker` fixture. One additional test was XFAIL. Therefore a
reported resolved result here does not establish a clean suite or old-test
regression coverage. The image has Python 3.9 and pytest 7.4.4 but lacks
`pytest-httpbin` and `pytest-mock` fixture dependencies. The base repository's
`setup.py` and `requirements.txt` specify different `pytest-httpbin` pins. Resolve and
pin the environment, verify all intended test statuses and reproduce on the
actual evaluator before treating any run as a benchmark result.

## Dependency diagnostics

The base repository pins `pytest-httpbin` to `0.0.7` in `setup.py` and `0.2.0`
in `requirements.txt`. Both variants were investigated without choosing one
as authoritative. The first wheel-only installs selected an incompatible
modern Werkzeug, so pytest could not import `httpbin`. The old versions pinned
by the repository were then downloaded with verified source hashes; four
source-only packages were built into wheels offline in an isolated container.
Derived images were built offline with per-wheel hashes and no network during
test execution. The original benchmark image was not modified.

Two different diagnostic configurations produced these results for **each**
of the two plugin versions:

| Configuration | Gold suite | Empty suite | Upstream parser on 113 targets |
|---|---|---|---|
| Repo-pinned pytest 2.8.7, `-p no:typeguard --assert=plain` | 244 passed, 2 failed, 1 xfailed, 1 xpassed | 240 passed, 6 failed, 1 xfailed, 1 xpassed | All 113 missing; no valid score |
| Image pytest 7.4.4 plus fixture dependencies, without old `py` pin | 243 passed, 3 failed, 1 xfailed, 1 xpassed | 239 passed, 7 failed, 1 xfailed, 1 xpassed | Gold: 4/4 new and 109/109 old pass; empty: 0/4 new and 109/109 old pass |

The repo-pinned pytest 2 executable and output format differ from what the
upstream evaluator expects; test identifiers also differ. Earlier attempts
using the expected `pytest` executable therefore did not collect tests. A
first pytest 7 attempt with the repo's old `py` package also failed before
test collection. These failures are retained in
[`evaluator-dependency-diagnostics.jsonl`](evaluator-dependency-diagnostics.jsonl)
alongside the later controls; the file contains 16 summaries, not raw logs or
gold patches. Its SHA-256 is
`1915290e725167b62f3997fd2fec26ed9e3108d2abef59c40f54ba0e856040de`.

For pytest 7, the three failures common to gold and empty are two SSL tests
reporting `CA_MD_TOO_WEAK` and a test using a string form of `pytest.raises`
that pytest 7 rejects. The four additional empty-patch failures are the selected
FAIL_TO_PASS tests. All 113 selected test statuses were parsed in these four
pytest 7 controls, and the upstream grader reported gold resolved and empty
unresolved. This mixed environment is a diagnostic intervention: the image
uses pytest 7 while the repository requirements pin pytest 2. It is not an
unmodified official benchmark result and does not demonstrate full old-test
regression coverage.

A further isolated pytest 2 diagnostic found that the `pytest-httpbin` 0.0.7
server certificate had expired on 23 June 2025. Lowering the local OpenSSL
security level exposed the expiry but did not fix the two SSL failures.
Replacing the certificate in another derived image yielded 245 passed and one
failed for gold, versus 241 passed and five failed for empty; both had one
XFAIL and one XPASS. The replacement certificate had a subject alternative
name, unlike the fixture expected by one warning test, so that remaining
failure reflects a changed test condition. The upstream parser still missed
all 113 targets in both runs. This diagnostic is not a valid benchmark score;
the randomly generated certificate also makes the image build non-reproducible.

With another generated certificate preserving the fixture's no-SAN behavior,
the local pytest 2 diagnostic reported gold: 246 passed, one XFAIL and one
XPASS; empty: 242 passed, four failed, one XFAIL and one XPASS. The upstream
parser still recognized none of the 113 target IDs. An experimental post-run
adapter compared pytest 2 and pytest 7 collections by test name and parameter
value fingerprints, then mapped log statuses: gold had 4/4 FAIL_TO_PASS and
109/109 PASS_TO_PASS passing; empty had 0/4 and 109/109, respectively. The
same image was run twice per control and all 248 mapped test statuses matched.
The normalized status hashes were
`9f031150fb7baa8439723e0febd8e388289736a9e9f7ebe6fcbf23733140c533` (gold)
and `d2e87a73855096436381a93dfcd041962b9ab56dd8a95e4afc12f17103465b7a` (empty).
The
adapter rejected ambiguous IDs and conflicting or missing duplicate statuses
in three synthetic tests. This is a local diagnostic, not an official score:
the adapter is not integrated into the evaluator, its handling of all pytest
semantics is unproven, log text can be spoofed by tested code, and the image
uses a randomly generated certificate and is not yet portably reproducible.
The adapter, collection data and gold-bearing logs remain local.

A local diagnostic wrapper now checks the candidate patch separately against
the pinned base before combining it with the test patch. A malformed candidate
is rejected as unscorable instead of being silently ignored. After pinning the
local evaluator sources and helpers, repeated gold and empty controls retained
the same 113 target statuses and suite totals. The wrapper re-collects tests
after applying each candidate, but it is not the upstream evaluator and does
not make the fixture image reproducible or prevent test code from spoofing
log output. The source, logs and evaluator-only fields remain outside the
agent workspace.

The local derived image IDs for the pytest 7 controls were
`sha256:66b065d28b65aaa27e319edbf4a5670f5673b67566bc2780a9c753fbafce40d5`
and `sha256:be467e0f6cc8e6511deb2b5684ab955635d874167a2609df04f345321c829fe0`.
Their corresponding wheel-lock hashes were
`6538b8164e92215d7f657b3ad076ca40d0e709fa962e63965cd7589b927acfac`
and `4d2ab57cdaf82445d8cc19d5f3250d58e20e5ea3f1f8ee5ea589ada1cd867e6c`.
The locks, wheels and full logs are retained locally, not redistributed here;
the Docker build and evaluator adapter are not yet packaged as a portable,
one-command reproduction. No model or agent patch was involved.

The controls used SWE-EVO source at `9b83d5af943ba7a17567336f5b18239f73960219`
with a local adapter that replaces container creation and isolates the network;
unused Modal and collection imports were stubbed. The adapter and environment
are not yet a locked, portable reproduction of the upstream CLI. Python 3.12.11
and Docker SDK 7.1.0 were observed in the host-side evaluator environment; its
dependencies were not fully pinned. The recorded run durations, about 20–23
seconds each, include local orchestration and must not be extrapolated to the
48-task experiment.
