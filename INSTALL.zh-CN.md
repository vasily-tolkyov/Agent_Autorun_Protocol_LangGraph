# 安装说明

[English](INSTALL.md) | 简体中文

## 前置条件

- Python 3.11 或更高版本
- Git
- 可写的 Codex home 目录
- 可写的目标项目目录

## 默认安装位置

默认会安装到：

```text
%USERPROFILE%\.codex\skills\
```

如果设置了 `CODEX_HOME`，则优先使用该目录。

## 自动安装

```powershell
python scripts\install.py
```

安装脚本会自动：

1. 把打包好的 skill 复制到 Codex skills 目录。
2. 创建 `phase-stage-langgraph-runtime/.venv`。
3. 安装 LangGraph 运行时依赖。
4. 以 editable 模式安装 runtime 包。
5. 如 `.env` 不存在，则从 `.env.example` 生成。
6. 运行 `langgraph validate`。

## 可选参数

```powershell
python scripts\install.py --codex-home C:\Custom\CodexHome
python scripts\install.py --skip-runtime-setup
python scripts\install.py --start-server
python scripts\install.py --force
```

## 验证

```powershell
python scripts\validate_bundle.py
python skills\phase-stage-autoplan-entry\scripts\smoke_test_autoplan_entry.py
python skills\phase-stage-autorun-protocol\scripts\smoke_test_runtime_bridge.py
python skills\generator-critic-verification-loop\scripts\smoke_test_generator_critic_loop.py
```

## 升级说明

- 拉取新版本后重新运行安装脚本。
- 如果希望覆盖已有安装，使用 `--force`。
- 升级后建议重新跑 smoke test。
- 这个 LangGraph 版本与 `Agent_Autorun_Protocol` 的工作流保持一致，但依赖 LangGraph 运行环境，而不是原来的 ACL-X 文件型 runtime。
