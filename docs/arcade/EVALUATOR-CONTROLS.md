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

The controls used SWE-EVO source at `9b83d5af943ba7a17567336f5b18239f73960219`
with a local adapter that replaces container creation and isolates the network;
unused Modal and collection imports were stubbed. The adapter and environment
are not yet a locked, portable reproduction of the upstream CLI. Python 3.12.11
and Docker SDK 7.1.0 were observed in the host-side evaluator environment; its
dependencies were not fully pinned. The recorded run durations, about 20–23
seconds each, include local orchestration and must not be extrapolated to the
48-task experiment.
