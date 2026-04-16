---
name: phase-stage-autorun-protocol
description: "Automatically drive long-running, multi-phase engineering work from ordered Markdown phase/stage plans through the shared LangGraph runtime, invoke generator-critic-verification-loop after each verified stage, and stop only for real blockers or missing plan detail."
---

# Phase Stage Autorun Protocol

Use this skill as the run policy for long, staged engineering work that should keep moving without routine human nudges.

The outer controller now runs on LangGraph.

- LangGraph thread state and checkpoints are authoritative
- `runtime-view.aclx`, `queue.md`, `status.json`, and `resume-handle.json` are exports and compatibility views
- do not revive or trust legacy `run-package.aclx`, checkpoint deltas, or snapshot artifacts from v1

Use it together with [$generator-critic-verification-loop](../generator-critic-verification-loop/SKILL.md). The verification loop normally runs as an autorun subgraph, not as a separate top-level workflow.

## Runtime behavior

- start in `t0` while bootstrapping the approved plan
- promote to `t3` on the first real executor, critic, or refiner interrupt, or any resumable loop
- keep one stable execution queue derived from the approved planning exports
- stop only for `missing_plan`, `missing_tool`, `destructive_action`, `conflicting_state`, `unresolved_contract`, or `strategy_change_required`

## Required workflow

Use `scripts/run_phase_stage_autorun.py` as the skill entry wrapper. It proxies to the shared runtime app at `../phase-stage-langgraph-runtime/scripts/phase_stage_client.py`.

- `bootstrap`: compatibility alias that maps to `approve` on the LangGraph planning thread
- `status`: inspect autorun handles and thread state
- `continue`: resume the current autorun interrupt with an executor or verifier result
- `resume`: same as `continue`, but use it when recovery is the explicit user intent
- `export`: refresh `runtime-view.aclx`, `queue.md`, and `status.json` from current graph state
- `server`: start, stop, or inspect the local `langgraph dev` supervisor

## Queue and stage rules

- read the approved `autorun-protocol.md` plus stage plans under `<project-root>/plans/phase-stage-langgraph/<runId>/`
- write runtime exports under `<project-root>/.codex/phase-stage-langgraph/<runId>/`
- do not skip stages, reorder stages, or silently merge stages
- when the queue reaches a pending next phase, block with `missing_plan` and request `expand-phase`
- after a successful executor result, route immediately into the verification subgraph
- advance the queue only after the stage is complete, audited, repaired as needed, and marked safe to continue from

## Child-result contract

Whenever you resume an autorun interrupt, send a result with:

- `summary`
- `changed_files`
- `verification_evidence`
- `verdict_or_status`
- `blocker_or_none`
- `recommended_next_action`
- `state_delta`

Do not continue on prose alone. Reduce the result back into LangGraph state first.

## Local operations

- let the wrapper manage the local `langgraph dev` server
- let the wrapper maintain `resume-handle.json`
- use `scripts/smoke_test_runtime_bridge.py` as the v2 smoke test entry
- leave legacy bridge helpers in read-only historical status; the active workflow is the LangGraph client/server path
