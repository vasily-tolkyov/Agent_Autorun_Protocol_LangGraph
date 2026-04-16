# Agent Autorun Protocol LangGraph

[![validate](https://github.com/vasily-tolkyov/Agent_Autorun_Protocol_LangGraph/actions/workflows/validate.yml/badge.svg)](https://github.com/vasily-tolkyov/Agent_Autorun_Protocol_LangGraph/actions/workflows/validate.yml)

English | [简体中文](README.zh-CN.md)

This is the LangGraph edition of [Agent_Autorun_Protocol](https://github.com/vasily-tolkyov/Agent_Autorun_Protocol).

It keeps the same staged workflow:

- `phase-stage-autoplan-entry` turns a vague task into an executable phase/stage plan.
- `phase-stage-autorun-protocol` advances the approved plan through a stable execution queue.
- `generator-critic-verification-loop` enforces post-stage audit, repair planning, and repeated verification.

The main change is the runtime layer:

- LangGraph thread state and checkpoints are authoritative.
- ACL-X remains as a compact export and compatibility format, not runtime truth.
- the workflow now expects a local LangGraph-capable Python environment

## Release Scope

This repository is for users who want the same workflow shape as the original project, but with a more durable local runtime:

- resumable LangGraph threads
- checkpoint-backed execution
- local `langgraph dev` supervision
- automatic environment bootstrap
- Codex skill entrypoints preserved

If you want the original ACL-X file-runtime edition, use [Agent_Autorun_Protocol](https://github.com/vasily-tolkyov/Agent_Autorun_Protocol).

## Included In This Repository

```text
skills/
  phase-stage-autoplan-entry/
  phase-stage-autorun-protocol/
  generator-critic-verification-loop/
  phase-stage-langgraph-runtime/
scripts/
  install.py
  install.ps1
  validate_bundle.py
```

## Quick Start

1. Install the bundle:

```powershell
python scripts\install.py
```

2. Validate the package:

```powershell
python scripts\validate_bundle.py
```

3. Optionally run the smoke tests:

```powershell
python %USERPROFILE%\.codex\skills\phase-stage-autoplan-entry\scripts\smoke_test_autoplan_entry.py
python %USERPROFILE%\.codex\skills\phase-stage-autorun-protocol\scripts\smoke_test_runtime_bridge.py
python %USERPROFILE%\.codex\skills\generator-critic-verification-loop\scripts\smoke_test_generator_critic_loop.py
```

4. Start planning from Codex:

```text
Use $phase-stage-autoplan-entry to plan the task.
```

5. After approval, continue execution:

```text
Use $phase-stage-autorun-protocol to execute the approved plan.
```

## Automatic Setup

The installer handles the LangGraph runtime bootstrap for you:

- copies the bundled skills into `CODEX_HOME/skills`
- creates `phase-stage-langgraph-runtime/.venv`
- installs `langgraph-cli[inmem]`, `langgraph`, `langgraph-sdk`, `langchain-core`, `langgraph-checkpoint-sqlite`, and `python-dotenv`
- installs the shared runtime package in editable mode
- seeds `.env` from `.env.example` when needed
- runs `langgraph validate`
- optionally starts the local LangGraph development server

Windows PowerShell wrapper:

```powershell
.\scripts\install.ps1
```

## Documentation

- [Installation Guide](INSTALL.md)
- [安装说明](INSTALL.zh-CN.md)
- [Changelog](CHANGELOG.md)
- [更新日志](CHANGELOG.zh-CN.md)
- [Runtime README](skills/phase-stage-langgraph-runtime/README.md)
- [运行时说明](skills/phase-stage-langgraph-runtime/README.zh-CN.md)

## Release Status

This repository is the published release bundle for the LangGraph-based workflow. It is intended to be cloned, installed, and used directly as a standalone distribution.
