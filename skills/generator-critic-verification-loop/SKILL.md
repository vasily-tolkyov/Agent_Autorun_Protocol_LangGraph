---
name: generator-critic-verification-loop
description: Dual-mode three-agent execution, verification, and repair-planning loop for high-risk work where one pass is likely to miss defects. In v2, the runtime-backed mode is hosted by the shared LangGraph app and usually runs as a subgraph of phase-stage-autorun-protocol.
---

# Generator Critic Verification Loop

Use this skill when a real generator, critic, and refiner loop needs machine-managed state, stop rules, and resumable interrupts.

Keep pure discussion, design-only exploration, or work that only edits runtime wiring in `t0`.

## Runtime model

- LangGraph thread state is authoritative in runtime mode
- ACL-X remains useful for compact exports, packets, and compatibility views, but not as recovery truth
- the loop usually runs as the `generator_critic_loop` subgraph inside [$phase-stage-autorun-protocol](../phase-stage-autorun-protocol/SKILL.md)
- use this skill as a standalone top-level entry only when you are debugging or driving the verification loop independently

## Stop rules

- accept after 5 consecutive `PASS` verdicts
- fail after 10 consecutive `FAIL` verdicts
- if the same blocking issue survives 2 failed rounds, set `strategy_change_required=true`

## Role boundaries

- generator executes the current approved plan
- critic verifies and returns `PASS` or `FAIL`
- refiner returns a repair plan only
- the main agent owns routing, checkpointing, judgment, and every state transition

## Required workflow

Use `scripts/run_generator_critic_loop.py` as the standalone wrapper when you need to drive this graph directly.

- `continue`: start or resume the loop with `--input-json` or an executor result
- `resume`: continue from the current interrupt explicitly as a recovery action
- `status`: inspect handles and thread state
- `export`: refresh compatibility exports from current graph state
- `server`: start, stop, or inspect the shared local `langgraph dev` supervisor

## Result contract

Every runtime resume payload should include:

- `summary`
- `changed_files`
- `verification_evidence`
- `verdict_or_status`
- `blocker_or_none`
- `recommended_next_action`
- `state_delta`

## References

- Read [references/runtime-contract.md](references/runtime-contract.md) and [references/runtime-packets.md](references/runtime-packets.md) when you need the packet schema.
- Use `scripts/smoke_test_generator_critic_loop.py` to verify the standalone wrapper locally.
