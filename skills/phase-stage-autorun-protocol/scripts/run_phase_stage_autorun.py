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
        description="LangGraph-backed autorun wrapper for the phase/stage workflow."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap")
    bootstrap.add_argument("--planning-root")
    bootstrap.add_argument("--controlling-protocol-path")
    bootstrap.add_argument("--run-root")
    bootstrap.add_argument("--run-id")
    bootstrap.add_argument("--title")
    bootstrap.add_argument("--no-status", action="store_true")

    status = subparsers.add_parser("status")
    status.add_argument("--project-root")
    status.add_argument("--run-id")
    status.add_argument("--planning-root")
    status.add_argument("--runtime-root")

    cont = subparsers.add_parser("continue")
    cont.add_argument("--project-root")
    cont.add_argument("--run-id")
    cont.add_argument("--planning-root")
    cont.add_argument("--runtime-root")
    cont.add_argument("--executor-result-json")
    cont.add_argument("--input-json")

    resume = subparsers.add_parser("resume")
    resume.add_argument("--project-root")
    resume.add_argument("--run-id")
    resume.add_argument("--planning-root")
    resume.add_argument("--runtime-root")
    resume.add_argument("--executor-result-json")
    resume.add_argument("--input-json")

    export = subparsers.add_parser("export")
    export.add_argument("--project-root")
    export.add_argument("--run-id")
    export.add_argument("--planning-root")
    export.add_argument("--runtime-root")

    server = subparsers.add_parser("server")
    server.add_argument("action", choices=["start", "status", "stop"], nargs="?", default="status")
    return parser


def add_context_args(client_args: list[str], args: argparse.Namespace) -> list[str]:
    if getattr(args, "project_root", None):
        client_args.extend(["--project-root", args.project_root])
    if getattr(args, "run_id", None):
        client_args.extend(["--run-id", args.run_id])
    if getattr(args, "planning_root", None):
        client_args.extend(["--planning-root", args.planning_root])
    if getattr(args, "runtime_root", None):
        client_args.extend(["--runtime-root", args.runtime_root])
    return client_args


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "bootstrap":
        planning_root = args.planning_root
        if not planning_root and args.controlling_protocol_path:
            planning_root = str(Path(args.controlling_protocol_path).resolve().parent)
        if not planning_root:
            raise SystemExit("bootstrap requires --planning-root or --controlling-protocol-path")
        return invoke(["approve", "--planning-root", planning_root])

    if args.command == "status":
        return invoke(add_context_args(["status"], args))

    if args.command == "continue":
        client_args = add_context_args(["continue", "--graph-id", "phase_stage_autorun"], args)
        if args.executor_result_json:
            client_args.extend(["--executor-result-json", args.executor_result_json])
        if args.input_json:
            client_args.extend(["--input-json", args.input_json])
        return invoke(client_args)

    if args.command == "resume":
        client_args = add_context_args(["resume", "--graph-id", "phase_stage_autorun"], args)
        if args.executor_result_json:
            client_args.extend(["--executor-result-json", args.executor_result_json])
        if args.input_json:
            client_args.extend(["--input-json", args.input_json])
        return invoke(client_args)

    if args.command == "export":
        return invoke(add_context_args(["export", "--graph-id", "phase_stage_autorun"], args))

    if args.command == "server":
        return invoke(["server", args.action])

    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
