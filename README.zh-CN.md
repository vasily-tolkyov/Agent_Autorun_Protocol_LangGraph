# Agent Autorun Protocol LangGraph

[![validate](https://github.com/vasily-tolkyov/Agent_Autorun_Protocol_LangGraph/actions/workflows/validate.yml/badge.svg)](https://github.com/vasily-tolkyov/Agent_Autorun_Protocol_LangGraph/actions/workflows/validate.yml)

[English](README.md) | 简体中文

这是 [Agent_Autorun_Protocol](https://github.com/vasily-tolkyov/Agent_Autorun_Protocol) 的 LangGraph 发布版。

它保留了与原项目相同的工作流骨架：

- `phase-stage-autoplan-entry`：把模糊任务整理成可执行的 phase/stage 计划。
- `phase-stage-autorun-protocol`：沿着已批准的计划和稳定队列持续推进。
- `generator-critic-verification-loop`：在每个阶段后执行审核、修复规划和重复验证。

真正变化的是底层 runtime：

- LangGraph 的 thread state 和 checkpoint 是唯一权威状态源。
- ACL-X 继续保留，但只作为紧凑导出和兼容格式，不再是真实运行时状态。
- 整个工作流现在依赖本地可用的 LangGraph Python 环境。

## 这个发布版解决什么问题

这个仓库适合想继续使用原始工作流、但希望把底层运行时切到 LangGraph 的用户：

- 支持可恢复的 LangGraph thread
- 支持 checkpoint 驱动的阶段执行
- 支持本地 `langgraph dev` 监督和复用
- 自带自动环境初始化
- 保留 Codex skill 入口体验

如果你需要的是原始 ACL-X 文件型 runtime，请使用 [Agent_Autorun_Protocol](https://github.com/vasily-tolkyov/Agent_Autorun_Protocol)。

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

## 快速开始

1. 安装整个 bundle：

```powershell
python scripts\install.py
```

2. 验证打包内容：

```powershell
python scripts\validate_bundle.py
```

3. 如有需要，运行 smoke test：

```powershell
python %USERPROFILE%\.codex\skills\phase-stage-autoplan-entry\scripts\smoke_test_autoplan_entry.py
python %USERPROFILE%\.codex\skills\phase-stage-autorun-protocol\scripts\smoke_test_runtime_bridge.py
python %USERPROFILE%\.codex\skills\generator-critic-verification-loop\scripts\smoke_test_generator_critic_loop.py
```

4. 在 Codex 中从规划开始：

```text
Use $phase-stage-autoplan-entry to plan the task.
```

5. 计划批准后继续执行：

```text
Use $phase-stage-autorun-protocol to execute the approved plan.
```

## 自动配置能力

安装脚本会自动完成 LangGraph 环境初始化：

- 将打包好的 skills 复制到 `CODEX_HOME/skills`
- 创建 `phase-stage-langgraph-runtime/.venv`
- 安装 `langgraph-cli[inmem]`、`langgraph`、`langgraph-sdk`、`langchain-core`、`langgraph-checkpoint-sqlite` 和 `python-dotenv`
- 以 editable 模式安装共享 runtime 包
- 需要时从 `.env.example` 生成 `.env`
- 执行 `langgraph validate`
- 可选启动本地 LangGraph 开发服务器

PowerShell 包装入口：

```powershell
.\scripts\install.ps1
```

## 文档导航

- [Installation Guide](INSTALL.md)
- [安装说明](INSTALL.zh-CN.md)
- [Changelog](CHANGELOG.md)
- [更新日志](CHANGELOG.zh-CN.md)
- [Runtime README](skills/phase-stage-langgraph-runtime/README.md)
- [运行时说明](skills/phase-stage-langgraph-runtime/README.zh-CN.md)

## 发布状态

这个仓库就是 LangGraph 版工作流的正式发布包，可直接克隆、安装并使用。
