# Planning estimate (not measured)

Status: no API calls or benchmark runs. This is a scenario for budgeting, not a spending limit or an estimate based on measured trajectories.

Proposed fixed model: OpenAI `gpt-4.1-2025-04-14`, temperature 0, seeds 1, 2 and 3, with seed 1 designated for the primary McNemar analysis. The snapshot, endpoint, account access, model availability, and transmission of those parameters through OpenHands need verification. OpenAI describes the Chat Completions seed parameter as deprecated, best effort, and not a determinism guarantee. OpenHands can alter temperature on a retry; the experiment must detect and prevent that before running. The model is a candidate for a controlled comparison, not a claim that it is optimal.

On 2026-10-26, [OpenAI's GPT-4.1 model documentation](https://developers.openai.com/api/docs/models/gpt-4.1) lists standard text input at $2 and output at $8 per million tokens. Cached input is priced differently; the scenarios below conservatively assume no cache discount. Verify current rates before purchase. [Chat Completions API reference](https://platform.openai.com/docs/api-reference/chat/create) describes seed limitations.

There are 48 tasks × 2 arms × 3 seeds = 288 initial trajectories and at most 144 × 2 = 288 repair rounds in the arcade arm. Illustrative token totals are assumed **per trajectory** and **per repair round**, not measurements:

| Scenario | Initial input / output | Repairs assumed | Repair input / output | Model cost |
|---|---|---|---|---:|
| Low | 0.25M / 0.02M | 144 rounds | 0.10M / 0.005M | $224.64 |
| Middle | 1M / 0.05M | 144 rounds | 0.25M / 0.01M | $774.72 |
| High | 2M / 0.10M | 288 rounds | 0.50M / 0.02M | $1,716.48 |

For example, middle = 288 × (1 × $2 + 0.05 × $8) + 144 × (0.25 × $2 + 0.01 × $8). These scenarios are not bounds; long contexts, retries, failed requests, rate changes and different repair rates can exceed them. They exclude compute, storage, network, taxes, pilot runs, repeated evaluations and the optional sequential experiment. The host is ARM64 and benchmark-image compatibility is unverified; x86 infrastructure may incur additional cost. Before seeking final approval for a full run, measure representative token use, image size, runtime and grading costs in a separately approved bounded pilot, and establish an enforceable spending ceiling and cancellation policy.
