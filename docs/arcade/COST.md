# Planning estimate (not measured)

The owner requested OpenRouter with a free model first, replacing the earlier
GPT-6 Luna subscription plan. The current pilot candidate is
`cohere/north-mini-code:free` on provider Cohere. On 27 October 2026,
[OpenRouter's model page](https://openrouter.ai/cohere/north-mini-code:free)
and endpoint metadata showed zero prompt and completion price. Synthetic API tool-call checks reported zero cost; no benchmark trajectory has run.
These checks do not establish the future price, availability, or the bill for a
full experiment.

If all 288 initial trajectories and repairs use only the same zero-priced
endpoint, the expected model-token charge is **$0**. This is a conditional
estimate, not a measured total or spending cap. The eventual runner must enforce
the fixed `:free` model, the selected provider, no fallback and zero maximum
price for every request, and stop when those checks cannot be met. The separate
synthetic probe enforces request constraints; the Codex agent loop does not yet
prove that it does. Do not purchase credits, use a paid model or start the full
experiment without the owner's separate approval.

The planned design has 48 tasks × 2 arms × 3 independent repetitions, plus up
to 288 guard-repair rounds. A trajectory can require many API requests.
[OpenRouter pricing](https://openrouter.ai/pricing) currently describes free
model limits of 20 requests/minute and 50 requests/day, increasing to 1,000/day
for accounts that have purchased at least $10 in credits. Actual account
eligibility, trajectory length, retry behavior and queueing remain unmeasured;
these limits are requests, not trajectories. An estimate of completion time and
local compute usage requires a bounded pilot.

Even if every one of the 288 initial trajectories used only one request, that
would require at least 288 requests: six daily allowance windows at 50/day, or
one at 1,000/day, assuming no other use and uninterrupted availability. Real
trajectories, repair rounds and retries may need more. This is a mathematical
lower bound, not a measured duration or a claim about this account's allowance.

The estimate excludes local electricity, storage, network and any optional
external compute. The inspected host is ARM64 while benchmark images are x86-64;
emulation and image capacity have not been validated across the suite. Pricing
and availability can change, and a zero-cost API does not eliminate runtime or
resource limits. Only public task context may be sent to the provider; gold and
internal material must remain inaccessible to the model and tool subprocesses.
