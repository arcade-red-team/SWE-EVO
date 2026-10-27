# Planning estimate (not measured)

Status: no model calls or benchmark runs. The owner approved the choice of Codex with `gpt-6-luna` at reasoning effort `low` and three repetitions, but has **not** approved the full experiment. This estimate is not a spending limit or a prediction from measured trajectories.

## Approved subscription route

Use Codex signed in with the owner's ChatGPT account, subject to the plan's Codex allowance. Calls within the included allowance do not incur a separate per-token API charge; they consume quota shared with other Codex/Work activity. Once the allowance is exhausted, extra usage may consume credits depending on account settings. Confirm those settings and set a hard stop before any credit or other paid overage. API pricing is not a forecast of subscription quota, credit consumption, or dollars actually charged. [OpenAI: ChatGPT Work and Codex](https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex)

There are 48 tasks × 2 arms × 3 independently started repetitions = 288 initial trajectories, plus at most 144 × 2 = 288 arcade repair rounds. Repetition numbers are labels, not verified model seeds. We cannot infer whether the current subscription allowance covers 288 long-running trajectories. A bounded pilot should measure actual usage and timing before setting the full-run quota budget; do not treat token totals as a way to predict subscription usage. The full run remains contingent on explicit approval and on the technical blockers in SETUP.md being resolved.

## Separate API price illustration

This section is an illustrative alternative **if using the OpenAI API separately**, not a charge for the approved subscription route. On 2026-10-26, [GPT-6 Luna API documentation](https://developers.openai.com/api/docs/models/gpt-6-luna) lists standard text input at $0.10 and output at $0.50 per million tokens. The examples assume standard rates, no cache discount, and no requests above the long-context threshold. Totals are assumed **per trajectory** and **per repair round**, not measurements:

| Scenario | Initial input / output | Repairs assumed | Repair input / output | Illustrative API cost |
|---|---|---|---|---:|
| Low | 0.25M / 0.02M | 144 rounds | 0.10M / 0.005M | $11.88 |
| Middle | 1M / 0.05M | 144 rounds | 0.25M / 0.01M | $40.32 |
| High | 2M / 0.10M | 288 rounds | 0.50M / 0.02M | $89.28 |

Middle = 288 × (1 × $0.10 + 0.05 × $0.50) + 144 × (0.25 × $0.10 + 0.01 × $0.50). An individual request with over 272K input tokens is priced at twice the applicable input rates and 1.5 times the output rate for that request; the table's trajectory totals do not reveal request sizes. As an extreme illustration, if all requests in these three scenarios exceeded that threshold, the costs would be $22.14, $76.68 and $169.92 respectively. Cache-write billing, retries, failed requests, rate changes and different repair rates can change cost. Neither set is a cap.

These figures exclude compute, storage, network, taxes, pilot runs, repeated evaluations and the optional sequential experiment. The inspected host is ARM64 and benchmark-image compatibility is unverified; x86 infrastructure may incur additional cost. Do not submit evaluator-only gold patches to the agent or expose internal material to external services.
