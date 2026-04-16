---
name: phase-stage-autoplan-entry
description: "Collect task context from the user request plus the target project, generate adaptive phase/stage Markdown engineering plans, stop in pending approval state, and then hand off approved plans to phase-stage-autorun-protocol through the shared LangGraph runtime."
---

# Phase Stage Autoplan Entry

Use this skill when the task does not already have an approved phase/stage plan.

Keep the planning pass in `t0`.

- do not start execution loops while planning
- do not auto-run the generated plan without explicit user confirmation
- treat LangGraph thread state as authoritative once the planning thread exists
- treat `planning-state.aclx` and Markdown files as compatibility and export artifacts, not as runtime truth

Use this skill together with [$phase-stage-autorun-protocol](../phase-stage-autorun-protocol/SKILL.md).

## Required workflow

Use `scripts/run_phase_stage_autoplan.py` as the skill entry wrapper. It proxies to the shared runtime app at `../phase-stage-langgraph-runtime/scripts/phase_stage_client.py`.

- `intake`: create or refresh the planning thread and write planning exports
- `status`: inspect current planning thread handles and state
- `approve`: resume the planning thread with explicit approval and bootstrap the sibling autorun graph
- `expand-phase`: resume the planning thread to materialize the next pending phase or a requested phase
- `server`: start, stop, or inspect the local `langgraph dev` supervisor

## Planning rules

- write planning exports under `<project-root>/plans/phase-stage-langgraph/<runId>/`
- write runtime exports under `<project-root>/.codex/phase-stage-langgraph/<runId>/`
- generate all phases up front
- leave future implementation phases in `detailStatus: pending` until they are expanded
- detailed stages must be executable and verifiable one at a time
- do not infer unplanned future stage detail just to keep the queue moving

## Authority model

- LangGraph thread checkpoints are the only authoritative planning state
- `planning-state.aclx` is a compact compatibility/export view of that state
- `autorun-protocol.md` and `phase-index.md` remain the human-readable control documents
- do not bootstrap or recover from legacy `.codex/phase-stage-autorun/<runId>/run-package.aclx`

## Approval and handoff

- explicit user confirmation in the Codex conversation is the approval signal
- after approval, run `approve` instead of hand-editing any planning artifact
- `approve` starts the `phase_stage_autorun` graph and writes refreshed exports plus `resume-handle.json`
- normal continuation after approval belongs to [$phase-stage-autorun-protocol](../phase-stage-autorun-protocol/SKILL.md)

## References

- Read [references/planning-contract.md](references/planning-contract.md) if you need the planning artifact contract.
- Use `scripts/smoke_test_autoplan_entry.py` to verify the LangGraph-backed wrapper locally.
