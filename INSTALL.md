# Installation

English | [简体中文](INSTALL.zh-CN.md)

## Prerequisites

- Python 3.11 or newer
- Git
- A writable Codex home directory
- A writable target project directory

## Default Install Target

By default the installer uses:

```text
%USERPROFILE%\.codex\skills\
```

If `CODEX_HOME` is set, the installer uses that instead.

## Automatic Install

```powershell
python scripts\install.py
```

The installer will:

1. Copy the bundled skills into your Codex skills directory.
2. Create `phase-stage-langgraph-runtime/.venv`.
3. Install the LangGraph runtime dependencies.
4. Install the runtime package in editable mode.
5. Seed `.env` from `.env.example` if it does not already exist.
6. Run `langgraph validate`.

## Optional Flags

```powershell
python scripts\install.py --codex-home C:\Custom\CodexHome
python scripts\install.py --skip-runtime-setup
python scripts\install.py --start-server
python scripts\install.py --force
```

## Validation

```powershell
python scripts\validate_bundle.py
python skills\phase-stage-autoplan-entry\scripts\smoke_test_autoplan_entry.py
python skills\phase-stage-autorun-protocol\scripts\smoke_test_runtime_bridge.py
python skills\generator-critic-verification-loop\scripts\smoke_test_generator_critic_loop.py
```

## Upgrade Notes

- Re-run the installer after pulling new changes.
- Use `--force` when you want to overwrite an existing skill installation.
- Re-run the smoke tests after upgrading.
- This LangGraph edition is workflow-compatible with `Agent_Autorun_Protocol`, but it requires the LangGraph runtime environment instead of the original ACL-X file runtime.
