# Installation

English | [简体中文](INSTALL.zh-CN.md)

## Requirements

- Python 3.11 or newer
- Git
- a writable Codex home directory
- a writable target project directory

## Default Install Target

By default the installer writes to:

```text
%USERPROFILE%\.codex\skills\
```

If `CODEX_HOME` is set, that directory is used instead.

## One-Step Install

```powershell
python scripts\install.py
```

The installer will:

1. Copy the bundled skills into your Codex skills directory.
2. Create `phase-stage-langgraph-runtime/.venv`.
3. Install the LangGraph runtime dependencies.
4. Install the shared runtime package in editable mode.
5. Seed `.env` from `.env.example` if needed.
6. Run `langgraph validate`.

PowerShell wrapper:

```powershell
.\scripts\install.ps1
```

## Optional Flags

```powershell
python scripts\install.py --codex-home C:\Custom\CodexHome
python scripts\install.py --skip-runtime-setup
python scripts\install.py --start-server
python scripts\install.py --force
```

## Validation

Validate the repository bundle:

```powershell
python scripts\validate_bundle.py
```

Smoke test the installed copy:

```powershell
python %USERPROFILE%\.codex\skills\phase-stage-autoplan-entry\scripts\smoke_test_autoplan_entry.py
python %USERPROFILE%\.codex\skills\phase-stage-autorun-protocol\scripts\smoke_test_runtime_bridge.py
python %USERPROFILE%\.codex\skills\generator-critic-verification-loop\scripts\smoke_test_generator_critic_loop.py
```

## Upgrade Notes

- Re-run the installer after pulling a new version.
- Use `--force` to overwrite an existing installed copy.
- Re-run the smoke tests after upgrading.
- This release keeps the same workflow as `Agent_Autorun_Protocol`, but requires the LangGraph runtime environment instead of the original ACL-X file runtime.
