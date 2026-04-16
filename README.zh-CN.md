# Agent Autorun Protocol LangGraph

[English](README.md) | 简体中文

这个仓库保留了与 [Agent_Autorun_Protocol](https://github.com/vasily-tolkyov/Agent_Autorun_Protocol) 相同的高层工作流，但把底层运行时替换成了本地 LangGraph 环境。

也就是说，工作流仍然是：

- `phase-stage-autoplan-entry` 负责把模糊任务整理成可执行的 phase/stage 计划
- `phase-stage-autorun-protocol` 负责持续推进已批准的计划
- `generator-critic-verification-loop` 负责每个阶段后的审核与修复闭环

真正变化的是运行时：

- LangGraph 的 thread state 和 checkpoint 才是唯一权威状态源
- ACL-X 文件只保留为兼容导出和压缩表达
- 这个版本必须有可用的 LangGraph 本地 Python 环境

## 仓库内容

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

## 自动配置

仓库内置了 LangGraph 运行时的自动配置逻辑：

- `scripts/install.py` 会把打包好的 skill 复制到你的 `CODEX_HOME/skills`
- 自动创建 `phase-stage-langgraph-runtime/.venv`
- 自动安装 `langgraph-cli[inmem]`、`langgraph`、`langgraph-sdk`、`langchain-core`、`langgraph-checkpoint-sqlite`
- 自动执行可编辑安装
- 如有需要会从 `.env.example` 生成 `.env`
- 自动校验 `langgraph.json`

Windows 下直接运行：

```powershell
python scripts\install.py
```

或者：

```powershell
.\scripts\install.ps1
```

## 快速开始

1. 运行安装脚本。
2. 验证打包内容：

```powershell
python scripts\validate_bundle.py
```

3. 运行 smoke test：

```powershell
python skills\phase-stage-autoplan-entry\scripts\smoke_test_autoplan_entry.py
python skills\phase-stage-autorun-protocol\scripts\smoke_test_runtime_bridge.py
python skills\generator-critic-verification-loop\scripts\smoke_test_generator_critic_loop.py
```

4. 从下面这句开始：

```text
Use $phase-stage-autoplan-entry to plan the task.
```

5. 批准后再继续：

```text
Use $phase-stage-autorun-protocol to execute the approved plan.
```

## LangGraph 依赖说明

这个仓库明确要求本地具备 LangGraph 运行环境。如果你想使用原始的 ACL-X 文件型 runtime 版本，请使用 [Agent_Autorun_Protocol](https://github.com/vasily-tolkyov/Agent_Autorun_Protocol)。

详细安装和升级说明见 [INSTALL.zh-CN.md](INSTALL.zh-CN.md)。
