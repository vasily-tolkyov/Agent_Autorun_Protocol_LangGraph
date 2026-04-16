# 安装说明

[English](INSTALL.md) | 简体中文

## 环境要求

- Python 3.11 或更高版本
- Git
- 可写的 Codex home 目录
- 可写的目标项目目录

## 默认安装位置

默认安装到：

```text
%USERPROFILE%\.codex\skills\
```

如果设置了 `CODEX_HOME`，则优先使用该目录。

## 一步安装

```powershell
python scripts\install.py
```

安装脚本会自动：

1. 将打包好的 skills 复制到你的 Codex skills 目录。
2. 创建 `phase-stage-langgraph-runtime/.venv`。
3. 安装 LangGraph 运行时依赖。
4. 以 editable 模式安装共享 runtime 包。
5. 需要时从 `.env.example` 生成 `.env`。
6. 执行 `langgraph validate`。

PowerShell 包装入口：

```powershell
.\scripts\install.ps1
```

## 可选参数

```powershell
python scripts\install.py --codex-home C:\Custom\CodexHome
python scripts\install.py --skip-runtime-setup
python scripts\install.py --start-server
python scripts\install.py --force
```

## 验证

验证仓库 bundle：

```powershell
python scripts\validate_bundle.py
```

验证已安装副本：

```powershell
python %USERPROFILE%\.codex\skills\phase-stage-autoplan-entry\scripts\smoke_test_autoplan_entry.py
python %USERPROFILE%\.codex\skills\phase-stage-autorun-protocol\scripts\smoke_test_runtime_bridge.py
python %USERPROFILE%\.codex\skills\generator-critic-verification-loop\scripts\smoke_test_generator_critic_loop.py
```

## 升级说明

- 拉取新版本后重新运行安装脚本。
- 如果要覆盖已有安装，请使用 `--force`。
- 升级后建议重新运行 smoke test。
- 这个发布版与 `Agent_Autorun_Protocol` 保持相同工作流，但要求使用 LangGraph 运行时环境，而不是原来的 ACL-X 文件型 runtime。
