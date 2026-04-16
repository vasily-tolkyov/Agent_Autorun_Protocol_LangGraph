# Planning Contract

Use this skill to create planning artifacts under:

```text
<project-root>/plans/phase-stage-langgraph/<runId>/
```

Required files:

- `task-intake.md`
- `task-context.json`
- `planning-state.aclx`
- `autorun-protocol.md`
- `phase-index.md`
- `phase-XX-*/phase.md`
- `phase-XX-*/stage-outline.md`
- `phase-XX-*/stage-YY-*.md` for ready phases only

Contract rules:

- keep the new skill in `t0`
- keep planning semantics in Markdown, but move control/index state into `planning-state.aclx`
- generate all phases upfront
- only generate detailed stage files for the current executable phase
- leave later phases as `detailStatus: pending` until `expand-phase`
- after explicit user confirmation, call the sibling `phase-stage-autorun-protocol` driver via `approve`
