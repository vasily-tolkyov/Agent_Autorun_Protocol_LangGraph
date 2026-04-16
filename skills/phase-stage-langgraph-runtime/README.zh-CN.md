# Phase/Stage LangGraph Runtime

[English](README.md) | 简体中文

这个包承载了以下 3 个 skill 共用的 LangGraph 运行时：

- `phase-stage-autoplan-entry`
- `phase-stage-autorun-protocol`
- `generator-critic-verification-loop`

## Runtime 模型

- LangGraph 的 thread state 和 SQLite checkpoint 是唯一权威状态源。
- 目标项目中的 planning 和 runtime 导出文件仍然保留，但只作为兼容视图。
- ACL-X 继续用于紧凑导出和 handoff packet，不再作为恢复依据。

## 重要路径

- runtime 应用根目录：
  `<CODEX_HOME>/skills/phase-stage-langgraph-runtime`
- planning 导出目录：
  `<project-root>\plans\phase-stage-langgraph\<runId>\`
- runtime 导出目录：
  `<project-root>\.codex\phase-stage-langgraph\<runId>\`
- 本地 checkpoint 存储：
  `var\langgraph-checkpoints.sqlite`

## 安装方式

推荐直接使用仓库顶层安装脚本：

```powershell
python scripts\install.py
```

如果需要，也可以手动安装：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -U "langgraph-cli[inmem]" "langgraph" "langgraph-sdk" "langchain-core" "langgraph-checkpoint-sqlite" "python-dotenv"
.venv\Scripts\python -m pip install -e .
```

## 手动启动服务

```powershell
.venv\Scripts\langgraph.exe dev --config langgraph.json --host 127.0.0.1 --port 2024 --no-browser --no-reload
```

通常不需要手动执行，wrapper 会通过 `scripts\phase_stage_client.py` 自动管理。

## 统一客户端命令

可以通过 `scripts\phase_stage_client.py` 直接控制 runtime：

- `plan`
- `status`
- `approve`
- `expand-phase`
- `continue`
- `resume`
- `export`
- `server`

## Graph ID

- `phase_stage_planning`
- `phase_stage_autorun`
- `generator_critic_loop`
