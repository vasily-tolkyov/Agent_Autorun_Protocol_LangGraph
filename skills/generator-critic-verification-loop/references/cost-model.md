# Cost Model

These estimates are heuristic. The UCLA PDF does not provide a full token ledger, so use this file for budgeting rather than for exact accounting. This version assumes a three-agent loop with generator, critic, and refiner roles.

## Normalized token model

Let one baseline one-shot attempt cost `1.0x`.

Typical relative costs:

- initial generator execution: `1.0x`
- critic verification: `0.5x` to `0.9x`
- main-agent bug report review: `0.1x` to `0.2x`
- refiner repair planning: `0.3x` to `0.6x`
- generator repair execution: `0.7x` to `1.0x`

Approximate total:

`Total = G0 + n * (C + R + P + G) + m * C`

Where:

- `G0` = initial generator execution
- `n` = number of failed audit rounds that require repair
- `C` = critic verification cost
- `R` = main-agent review cost
- `P` = refiner planning cost
- `G` = generator re-execution cost
- `m` = required consecutive clean critic passes after the latest repaired candidate

## Expected overhead versus one-shot

Reasonable operating ranges:

- light three-agent loop:
  - 1 repair round
  - 2 clean passes
  - about `3.3x` to `5.3x` baseline
  - token increase: about `+230%` to `+430%`
- standard loop:
  - 1 to 2 repair rounds
  - 3 clean passes
  - about `5.0x` to `8.4x` baseline
  - token increase: about `+400%` to `+740%`
- strict 5-pass / 10-fail loop:
  - 2 to 3 repair rounds
  - 5 clean passes
  - about `7.2x` to `12.0x` baseline
  - token increase: about `+620%` to `+1100%`

## Expected quality lift

Do not claim a single exact percentage without a task-specific A/B test. The PDF mainly supports a directional conclusion: repeated independent verification improves rigorous correctness when the initial draft overlaps with a valid approach but still contains gaps.

Use these planning ranges:

- easy tasks:
  - absolute quality lift: `0%` to `5%`
  - relative lift: often not worth the extra cost
- medium difficulty, fixable drafts:
  - absolute quality lift: about `10%` to `25%`
  - relative lift: about `15%` to `60%`
- hard reasoning tasks with promising but flawed drafts:
  - absolute quality lift: about `20%` to `40%`
  - relative lift: about `50%` to `200%`

## Concrete anchor from the PDF

Facts stated or cited in the paper:

- the pipeline solves `5/6` IMO 2025 problems
- direct prompting quality is described as "pretty low"
- for Problem 3, the paper says their approach succeeded after sampling 20 initial solutions, while cited prior work observed that 32 direct samples were needed to get a rigorous solution with 50% probability

That Problem 3 comparison suggests roughly `37.5%` lower initial sampling burden for reaching one rigorous solve on that problem, although it is not a clean apples-to-apples pass-rate comparison.

## Budget advice

- Use the standard loop by default.
- Use the strict `5 PASS / 10 FAIL` gate when the user explicitly wants the full three-agent confidence loop.
- If token budget matters more than rigor, lower the clean-pass requirement and keep the refiner in the loop only for real failures.
