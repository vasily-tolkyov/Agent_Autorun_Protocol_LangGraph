# UCLA Verification And Refinement Notes

This note distills the method described in a local PDF reference on the UCLA-style verification method.

## Paper-derived flow

The pipeline in the PDF is:

1. Initial solution generation.
2. Self-improvement.
3. Verification plus bug report generation.
4. Bug report review.
5. Correction or improvement based on the bug report.
6. Accept or reject.

The flow loops through steps 3 to 5 until a stopping condition is met.

## Why the self-refinement step exists

The paper says a single Gemini 2.5 Pro run often exhausts the available thinking budget. The self-improvement step effectively buys another full reasoning pass before verification. In a generator/critic skill, this maps cleanly to a generator self-review round before the critic sees the draft.

## Verifier behavior to preserve

The verifier is intentionally narrow:

- verify step by step
- do not solve
- do not fill gaps
- classify issues
- continue checking independent branches after a critical error
- continue downstream checking after a justification gap by temporarily assuming the disputed step

The paper distinguishes:

- critical errors: false statements or logical fallacies that break the proof
- justification gaps: insufficient rigor, which may be major or minor

For a more general skill, it is useful to split justification gaps into `Major Gap` and `Minor Gap`.

## Reliability claims from the paper

Qualitative claims reported in the PDF:

- critical errors are seldom missed
- if the verifier reports a critical error, it may occasionally overstate severity, but revision is almost always needed
- the verifier can over-report small gaps, so a review pass on the bug report is useful

This is why the main agent, not the critic, should own bug report review.

## Stopping rules copied from the paper

- accept only after the answer passes verification 5 consecutive times
- reject after major issues persist for 10 rounds

These thresholds are expensive. They are best kept for proof-heavy or very high-stakes work. For ordinary use, smaller thresholds are usually enough.

## Transfer to main-agent plus subagents

In Codex, the clean translation is:

- main agent = orchestration, state, and final judgment
- generator subagent = proposal and revision
- critic subagent = adversarial verification

Do not let the critic repair the answer during the same pass. Mixing roles weakens the signal.
