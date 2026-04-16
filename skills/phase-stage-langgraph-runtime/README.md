# Phase/Stage LangGraph Runtime

This package hosts the shared LangGraph v2 runtime used by:

- `phase-stage-autoplan-entry`
- `phase-stage-autorun-protocol`
- `generator-critic-verification-loop`

## Local runtime model

- LangGraph thread state and SQLite checkpoints are authoritative.
- Planning and runtime exports under the target project remain readable compatibility views.
- ACL-X is retained for compact exports and packets, not as recovery truth.

## Important paths

- runtime app root:
  `<CODEX_HOME>/skills/phase-stage-langgraph-runtime`
- planning exports:
  `<project-root>\plans\phase-stage-langgraph\<runId>\`
- runtime exports:
  `<project-root>\.codex\phase-stage-langgraph\<runId>\`
- local checkpoint store:
  `var\langgraph-checkpoints.sqlite`

## Local setup

Create the dedicated virtual environment and install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -U "langgraph-cli[inmem]" "langgraph" "langgraph-sdk" "langchain-core" "langgraph-checkpoint-sqlite"
.venv\Scripts\python -m pip install -e .
```

The top-level installer at `scripts/install.py` automates the copy, venv bootstrap, package install, `.env` seeding, and `langgraph validate` steps for you.

## Manual server start

```powershell
.venv\Scripts\langgraph.exe dev --config langgraph.json --host 127.0.0.1 --port 2024 --no-browser --no-reload
```

The wrappers normally manage this for you through `phase_stage_client.py server start`.

## Unified client commands

Use `scripts\phase_stage_client.py` for direct runtime control:

- `plan`
- `status`
- `approve`
- `expand-phase`
- `continue`
- `resume`
- `export`
- `server`

## Graph ids

- `phase_stage_planning`
- `phase_stage_autorun`
- `generator_critic_loop`
