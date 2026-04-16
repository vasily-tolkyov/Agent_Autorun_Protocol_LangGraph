# Agent Autorun Protocol LangGraph

English | [简体中文](README.zh-CN.md)

This repository packages the same high-level workflow as [Agent_Autorun_Protocol](https://github.com/vasily-tolkyov/Agent_Autorun_Protocol), but the runtime layer is replaced with a local LangGraph environment.

In practice, the workflow is still:

- `phase-stage-autoplan-entry` for turning a vague task into an executable phase/stage plan
- `phase-stage-autorun-protocol` for continuously advancing the approved plan
- `generator-critic-verification-loop` for enforcing a post-stage audit-and-repair gate

The main difference is the runtime model:

- LangGraph thread state and checkpoints are authoritative
- ACL-X files remain compact compatibility exports, not runtime truth
- the workflow requires a LangGraph-capable local Python environment

## What Is Included

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

## Automatic Setup

This repository includes automatic configuration for the LangGraph runtime.

- `scripts/install.py` copies the bundled skills into your `CODEX_HOME/skills`
- it creates `phase-stage-langgraph-runtime/.venv`
- it installs `langgraph-cli[inmem]`, `langgraph`, `langgraph-sdk`, `langchain-core`, and `langgraph-checkpoint-sqlite`
- it installs the runtime package in editable mode
- it seeds `.env` from `.env.example` when needed
- it validates the LangGraph config

Windows example:

```powershell
python scripts\install.py
```

Or:

```powershell
.\scripts\install.ps1
```

## Quick Start

1. Run the installer.
2. Validate the bundle:

```powershell
python scripts\validate_bundle.py
```

3. Run the bundled smoke tests:

```powershell
python skills\phase-stage-autoplan-entry\scripts\smoke_test_autoplan_entry.py
python skills\phase-stage-autorun-protocol\scripts\smoke_test_runtime_bridge.py
python skills\generator-critic-verification-loop\scripts\smoke_test_generator_critic_loop.py
```

4. Start from:

```text
Use $phase-stage-autoplan-entry to plan the task.
```

5. After approval, continue with:

```text
Use $phase-stage-autorun-protocol to execute the approved plan.
```

## LangGraph Requirement

This repository intentionally depends on a local LangGraph environment. If you want the original ACL-X file-runtime bundle instead, use [Agent_Autorun_Protocol](https://github.com/vasily-tolkyov/Agent_Autorun_Protocol).

## Installation Guide

See [INSTALL.md](INSTALL.md) for setup, validation, and upgrade notes.
