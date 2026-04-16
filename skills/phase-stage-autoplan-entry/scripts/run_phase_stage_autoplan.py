from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SKILLS_ROOT = SKILL_DIR.parent
RUNTIME_ROOT = SKILLS_ROOT / "phase-stage-langgraph-runtime"
CLIENT_SCRIPT = RUNTIME_ROOT / "scripts" / "phase_stage_client.py"


def venv_python_path() -> Path:
    scripts_dir = RUNTIME_ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    return scripts_dir / ("python.exe" if os.name == "nt" else "python")


def runtime_python() -> str:
    venv_python = venv_python_path()
    return str(venv_python if venv_python.exists() else Path(sys.executable).resolve())


def invoke(client_args: list[str]) -> int:
    command = [runtime_python(), str(CLIENT_SCRIPT), *client_args]
    completed = subprocess.run(command, cwd=str(RUNTIME_ROOT))
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="LangGraph-backed intake and planning wrapper for phase/stage workflow runs."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    intake = subparsers.add_parser("intake")
    intake.add_argument("--project-root", required=True)
    intake.add_argument("--run-id", required=True)
    intake.add_argument("--title", required=True)
    intake.add_argument("--task", required=True)
    intake.add_argument("--planning-root")
    intake.add_argument("--success-criteria", action="append", default=[])
    intake.add_argument("--constraint", action="append", dest="constraints", default=[])

    status = subparsers.add_parser("status")
    status.add_argument("--project-root")
    status.add_argument("--run-id")
    status.add_argument("--planning-root")
    status.add_argument("--runtime-root")

    approve = subparsers.add_parser("approve")
    approve.add_argument("--planning-root", required=True)
    approve.add_argument("--runtime-root")
    approve.add_argument("--no-status", action="store_true")

    expand = subparsers.add_parser("expand-phase")
    expand.add_argument("--planning-root", required=True)
    expand.add_argument("--phase-id")

    server = subparsers.add_parser("server")
    server.add_argument("action", choices=["start", "status", "stop"], nargs="?", default="status")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "intake":
        client_args = [
            "plan",
            "--project-root",
            args.project_root,
            "--run-id",
            args.run_id,
            "--title",
            args.title,
            "--task",
            args.task,
        ]
        if args.planning_root:
            client_args.extend(["--planning-root", args.planning_root])
        for item in args.success_criteria:
            client_args.extend(["--success-criteria", item])
        for item in args.constraints:
            client_args.extend(["--constraint", item])
        return invoke(client_args)

    if args.command == "status":
        client_args = ["status"]
        if args.project_root:
            client_args.extend(["--project-root", args.project_root])
        if args.run_id:
            client_args.extend(["--run-id", args.run_id])
        if args.planning_root:
            client_args.extend(["--planning-root", args.planning_root])
        if args.runtime_root:
            client_args.extend(["--runtime-root", args.runtime_root])
        return invoke(client_args)

    if args.command == "approve":
        return invoke(["approve", "--planning-root", args.planning_root])

    if args.command == "expand-phase":
        client_args = ["expand-phase", "--planning-root", args.planning_root]
        if args.phase_id:
            client_args.extend(["--phase-id", args.phase_id])
        return invoke(client_args)

    if args.command == "server":
        return invoke(["server", args.action])

    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
