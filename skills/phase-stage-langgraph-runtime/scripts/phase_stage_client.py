from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5


RUNTIME_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME_ROOT / "src"))

from phase_stage_langgraph_runtime.exports import (  # noqa: E402
    append_event,
    load_resume_handle,
    write_resume_handle,
    write_runtime_exports,
)
from phase_stage_langgraph_runtime.io_utils import now_iso, read_json, write_json  # noqa: E402
from phase_stage_langgraph_runtime import planning as planning_lib  # noqa: E402

DEFAULT_SERVER_URL = os.environ.get("PHASE_STAGE_LANGGRAPH_SERVER_URL", "http://127.0.0.1:2024")
DEFAULT_SERVER_PORT = int(os.environ.get("PHASE_STAGE_LANGGRAPH_SERVER_PORT", "2024"))
SERVER_VAR_DIR = RUNTIME_ROOT / "var"
SERVER_META_PATH = SERVER_VAR_DIR / "server.json"
SERVER_LOG_PATH = SERVER_VAR_DIR / "server.log"
ENV_EXAMPLE_PATH = RUNTIME_ROOT / ".env.example"
ENV_PATH = RUNTIME_ROOT / ".env"
RUNTIME_DEPENDENCIES = [
    "langgraph-cli[inmem]",
    "langgraph",
    "langgraph-sdk",
    "langchain-core",
    "langgraph-checkpoint-sqlite",
    "python-dotenv",
]
ASSISTANT_IDS = {
    "phase_stage_planning": str(uuid5(NAMESPACE_URL, "codex://phase-stage-langgraph-runtime/v2/phase_stage_planning")),
    "phase_stage_autorun": str(uuid5(NAMESPACE_URL, "codex://phase-stage-langgraph-runtime/v2/phase_stage_autorun")),
    "generator_critic_loop": str(uuid5(NAMESPACE_URL, "codex://phase-stage-langgraph-runtime/v2/generator_critic_loop")),
}


def venv_scripts_dir() -> Path:
    return RUNTIME_ROOT / ".venv" / ("Scripts" if os.name == "nt" else "bin")


def runtime_python_path() -> Path:
    return venv_scripts_dir() / ("python.exe" if os.name == "nt" else "python")


def langgraph_executable_path() -> Path:
    return venv_scripts_dir() / ("langgraph.exe" if os.name == "nt" else "langgraph")


def command_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if extra:
        env.update(extra)
    return env


def runtime_environment_ready() -> bool:
    return runtime_python_path().exists() and langgraph_executable_path().exists()


def ensure_env_file() -> None:
    if ENV_PATH.exists() or not ENV_EXAMPLE_PATH.exists():
        return
    ENV_PATH.write_text(ENV_EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")


def ensure_runtime_environment() -> None:
    ensure_env_file()
    if runtime_environment_ready():
        return
    subprocess.run(
        [sys.executable, "-m", "venv", str(RUNTIME_ROOT / ".venv")],
        cwd=str(RUNTIME_ROOT),
        env=command_env(),
        check=True,
        stdout=sys.stderr,
        stderr=sys.stderr,
    )
    subprocess.run(
        [str(runtime_python_path()), "-m", "pip", "install", "-U", "pip", "setuptools", "wheel"],
        cwd=str(RUNTIME_ROOT),
        env=command_env(),
        check=True,
        stdout=sys.stderr,
        stderr=sys.stderr,
    )
    subprocess.run(
        [str(runtime_python_path()), "-m", "pip", "install", "-U", *RUNTIME_DEPENDENCIES],
        cwd=str(RUNTIME_ROOT),
        env=command_env(),
        check=True,
        stdout=sys.stderr,
        stderr=sys.stderr,
    )
    subprocess.run(
        [str(runtime_python_path()), "-m", "pip", "install", "-e", "."],
        cwd=str(RUNTIME_ROOT),
        env=command_env(),
        check=True,
        stdout=sys.stderr,
        stderr=sys.stderr,
    )
    subprocess.run(
        [str(langgraph_executable_path()), "validate", "--config", str(RUNTIME_ROOT / "langgraph.json")],
        cwd=str(RUNTIME_ROOT),
        env=command_env(),
        check=True,
        stdout=sys.stderr,
        stderr=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if Path(sys.executable).resolve() != runtime_python_path().resolve():
        ensure_runtime_environment()
        result = subprocess.run([str(runtime_python_path()), __file__, *argv], env=command_env(), cwd=str(RUNTIME_ROOT))
        return result.returncode
    ensure_env_file()

    from langgraph_sdk import get_sync_client

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "server":
        payload = handle_server(args)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    ensure_server()
    client = get_sync_client(url=DEFAULT_SERVER_URL)

    if args.command == "plan":
        payload = command_plan(args, client, planning_lib, load_resume_handle, write_resume_handle, append_event)
    elif args.command == "status":
        payload = command_status(args, client, load_resume_handle)
    elif args.command == "approve":
        payload = command_approve(args, client, planning_lib, load_resume_handle, write_resume_handle, append_event, write_runtime_exports)
    elif args.command == "expand-phase":
        payload = command_expand_phase(args, client, planning_lib, load_resume_handle, write_resume_handle, append_event)
    elif args.command == "continue":
        payload = command_continue(args, client, planning_lib, load_resume_handle, write_resume_handle, append_event, write_runtime_exports)
    elif args.command == "resume":
        payload = command_continue(args, client, planning_lib, load_resume_handle, write_resume_handle, append_event, write_runtime_exports, is_resume=True)
    elif args.command == "export":
        payload = command_export(args, client, planning_lib, load_resume_handle, write_runtime_exports)
    else:
        raise SystemExit(f"Unsupported command: {args.command}")

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified LangGraph client for the phase/stage workflow.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan = subparsers.add_parser("plan")
    plan.add_argument("--project-root", required=True)
    plan.add_argument("--run-id", required=True)
    plan.add_argument("--title", required=True)
    plan.add_argument("--task", required=True)
    plan.add_argument("--planning-root")
    plan.add_argument("--success-criteria", action="append", default=[])
    plan.add_argument("--constraint", action="append", dest="constraints", default=[])

    status = subparsers.add_parser("status")
    status.add_argument("--project-root")
    status.add_argument("--run-id")
    status.add_argument("--planning-root")
    status.add_argument("--runtime-root")

    approve = subparsers.add_parser("approve")
    approve.add_argument("--planning-root", required=True)

    expand = subparsers.add_parser("expand-phase")
    expand.add_argument("--planning-root", required=True)
    expand.add_argument("--phase-id")

    cont = subparsers.add_parser("continue")
    cont.add_argument("--project-root")
    cont.add_argument("--run-id")
    cont.add_argument("--planning-root")
    cont.add_argument("--runtime-root")
    cont.add_argument("--graph-id", default="phase_stage_autorun")
    cont.add_argument("--executor-result-json")
    cont.add_argument("--input-json")

    resume = subparsers.add_parser("resume")
    resume.add_argument("--project-root")
    resume.add_argument("--run-id")
    resume.add_argument("--planning-root")
    resume.add_argument("--runtime-root")
    resume.add_argument("--graph-id", default="phase_stage_autorun")
    resume.add_argument("--executor-result-json")
    resume.add_argument("--input-json")

    export = subparsers.add_parser("export")
    export.add_argument("--project-root")
    export.add_argument("--run-id")
    export.add_argument("--planning-root")
    export.add_argument("--runtime-root")
    export.add_argument("--graph-id", default="phase_stage_autorun")

    server = subparsers.add_parser("server")
    server.add_argument("action", choices=["start", "status", "stop"], default="status", nargs="?")
    return parser


def server_health() -> bool:
    try:
        with urllib.request.urlopen(f"{DEFAULT_SERVER_URL}/ok", timeout=2) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def ensure_server() -> dict[str, Any]:
    if server_health():
        return {"status": "running", "url": DEFAULT_SERVER_URL}
    return start_server()


def runtime_package_installed() -> bool:
    try:
        importlib.metadata.version("phase-stage-langgraph-runtime")
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


def ensure_runtime_package_installed() -> None:
    if runtime_package_installed():
        return
    SERVER_VAR_DIR.mkdir(parents=True, exist_ok=True)
    with SERVER_LOG_PATH.open("a", encoding="utf-8") as log_handle:
        subprocess.run(
            [str(runtime_python_path()), "-m", "pip", "install", "-e", "."],
            cwd=str(RUNTIME_ROOT),
            env=command_env(),
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            check=True,
        )


def start_server() -> dict[str, Any]:
    if server_health():
        return {"status": "running", "url": DEFAULT_SERVER_URL}
    ensure_runtime_environment()
    ensure_runtime_package_installed()
    SERVER_VAR_DIR.mkdir(parents=True, exist_ok=True)
    with SERVER_LOG_PATH.open("a", encoding="utf-8") as log_handle:
        process_kwargs: dict[str, Any] = {
            "cwd": str(RUNTIME_ROOT),
            "stdout": log_handle,
            "stderr": subprocess.STDOUT,
            "env": command_env(),
        }
        if os.name == "nt":
            process_kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
                subprocess, "CREATE_NO_WINDOW", 0
            )
        else:
            process_kwargs["start_new_session"] = True
        process = subprocess.Popen(
            [
                str(langgraph_executable_path()),
                "dev",
                "--config",
                str(RUNTIME_ROOT / "langgraph.json"),
                "--host",
                "127.0.0.1",
                "--port",
                str(DEFAULT_SERVER_PORT),
                "--no-browser",
                "--no-reload",
            ],
            **process_kwargs,
        )
    for _ in range(120):
        if server_health():
            payload = {"status": "running", "url": DEFAULT_SERVER_URL, "pid": process.pid, "startedAt": now_iso()}
            write_json(SERVER_META_PATH, payload)
            return payload
        if process.poll() is not None:
            log_tail = ""
            if SERVER_LOG_PATH.exists():
                log_tail = "\n".join(
                    SERVER_LOG_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
                )
            raise RuntimeError(
                f"LangGraph server exited before becoming healthy at {DEFAULT_SERVER_URL}.\n{log_tail}"
            )
        time.sleep(0.5)
    raise RuntimeError(f"LangGraph server did not become healthy at {DEFAULT_SERVER_URL}")


def stop_server() -> dict[str, Any]:
    if not SERVER_META_PATH.exists():
        return {"status": "stopped"}
    meta = json.loads(SERVER_META_PATH.read_text(encoding="utf-8"))
    pid = meta.get("pid")
    if pid:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            try:
                os.kill(int(pid), signal.SIGTERM)
            except OSError:
                pass
    SERVER_META_PATH.unlink(missing_ok=True)
    return {"status": "stopped"}


def handle_server(args: argparse.Namespace) -> dict[str, Any]:
    if args.action == "start":
        return start_server()
    if args.action == "stop":
        return stop_server()
    status = {"status": "running" if server_health() else "stopped", "url": DEFAULT_SERVER_URL}
    if SERVER_META_PATH.exists():
        status["meta"] = json.loads(SERVER_META_PATH.read_text(encoding="utf-8"))
    return status


def ensure_assistant(client: Any, graph_id: str) -> dict[str, Any]:
    return client.assistants.create(
        graph_id=graph_id,
        assistant_id=ASSISTANT_IDS[graph_id],
        if_exists="do_nothing",
        name=graph_id,
    )


def create_and_join_run(
    client: Any,
    *,
    thread_id: str,
    assistant_id: str,
    input_payload: dict[str, Any] | None = None,
    command_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run = client.runs.create(
        thread_id,
        assistant_id,
        input=input_payload,
        command=command_payload,
    )
    return client.runs.join(thread_id, run["run_id"])


def thread_snapshot(client: Any, thread_id: str) -> dict[str, Any]:
    return {
        "thread": client.threads.get(thread_id),
        "state": client.threads.get_state(thread_id),
    }


def checkpoint_id_from_snapshot(snapshot: dict[str, Any]) -> str:
    checkpoint = snapshot["state"].get("checkpoint") or {}
    return str(checkpoint.get("checkpoint_id") or "none")


def planning_input_payload(
    planning_lib: Any,
    planning_root: str,
    assistant_id: str,
    thread_id: str,
) -> dict[str, Any]:
    task_context = planning_lib.load_task_context(planning_root)
    return {
        "graph_id": "phase_stage_planning",
        "assistant_id": assistant_id,
        "thread_id": thread_id,
        "run_id": task_context["runId"],
        "title": task_context["title"],
        "task": task_context["task"],
        "project_root": task_context["projectRoot"],
        "planning_root": task_context["planningRoot"],
        "runtime_root": task_context["runtimeRoot"],
        "success_criteria": task_context["successCriteria"],
        "constraints": task_context["constraints"],
    }


def resolve_context(args: argparse.Namespace) -> dict[str, str]:
    from phase_stage_langgraph_runtime.exports import load_resume_handle
    from phase_stage_langgraph_runtime.io_utils import read_json

    if getattr(args, "planning_root", None):
        task_context = read_json(Path(args.planning_root).resolve() / "task-context.json")
        return {
            "project_root": task_context["projectRoot"],
            "run_id": task_context["runId"],
            "planning_root": task_context["planningRoot"],
            "runtime_root": task_context["runtimeRoot"],
        }
    if getattr(args, "runtime_root", None):
        runtime_root = Path(args.runtime_root).resolve()
        handle = json.loads((runtime_root / "resume-handle.json").read_text(encoding="utf-8"))
        return {
            "project_root": handle["project_root"],
            "run_id": handle["run_id"],
            "planning_root": handle["planning_root"],
            "runtime_root": handle["runtime_root"],
        }
    if getattr(args, "project_root", None) and getattr(args, "run_id", None):
        return {
            "project_root": str(Path(args.project_root).resolve()),
            "run_id": args.run_id,
            "planning_root": str((Path(args.project_root).resolve() / "plans" / "phase-stage-langgraph" / args.run_id).resolve()),
            "runtime_root": str((Path(args.project_root).resolve() / ".codex" / "phase-stage-langgraph" / args.run_id).resolve()),
        }
    raise ValueError("Unable to resolve run context from the provided arguments.")


def command_plan(args: argparse.Namespace, client: Any, planning_lib: Any, load_resume_handle: Any, write_resume_handle: Any, append_event: Any) -> dict[str, Any]:
    assistant = ensure_assistant(client, "phase_stage_planning")
    context = {
        "project_root": str(Path(args.project_root).resolve()),
        "run_id": args.run_id,
        "planning_root": args.planning_root or str(planning_lib.planning_root_for(args.project_root, args.run_id)),
        "runtime_root": str(planning_lib.runtime_root_for(args.project_root, args.run_id)),
    }
    resume_handle = load_resume_handle(context["project_root"], context["run_id"])
    planning_handle = resume_handle.get("handles", {}).get("phase_stage_planning", {})
    thread_id = planning_handle.get("thread_id")
    if not thread_id:
        thread = client.threads.create(graph_id="phase_stage_planning", metadata={"run_id": args.run_id, "graph_id": "phase_stage_planning"})
        thread_id = str(thread["thread_id"])
    create_and_join_run(
        client,
        thread_id=thread_id,
        assistant_id=assistant["assistant_id"],
        input_payload={
            "graph_id": "phase_stage_planning",
            "assistant_id": assistant["assistant_id"],
            "thread_id": thread_id,
            "run_id": args.run_id,
            "title": args.title,
            "task": args.task,
            "project_root": context["project_root"],
            "planning_root": context["planning_root"],
            "runtime_root": context["runtime_root"],
            "success_criteria": args.success_criteria,
            "constraints": args.constraints,
        },
    )
    snapshot = thread_snapshot(client, thread_id)
    state_values = dict(snapshot["state"]["values"])
    state_values.update({"assistant_id": assistant["assistant_id"], "thread_id": thread_id})
    resume_handle["handles"] = dict(resume_handle.get("handles") or {})
    resume_handle["handles"]["phase_stage_planning"] = {
        "graph_id": "phase_stage_planning",
        "assistant_id": assistant["assistant_id"],
        "thread_id": thread_id,
        "checkpoint_id": checkpoint_id_from_snapshot(snapshot),
        "status": snapshot["thread"]["status"],
        "updated_at": now_iso(),
    }
    resume_handle.update(
        {
            "version": "phase-stage-langgraph/codex-v2",
            "server_url": DEFAULT_SERVER_URL,
            "run_id": args.run_id,
            "project_root": context["project_root"],
            "planning_root": context["planning_root"],
            "runtime_root": context["runtime_root"],
            "active_graph": "phase_stage_planning",
            "updated_at": now_iso(),
        }
    )
    write_resume_handle(context["project_root"], context["run_id"], resume_handle)
    append_event(context["project_root"], context["run_id"], "plan", {"thread_id": thread_id})
    return {
        **planning_lib.export_planning_state(planning_lib.load_task_context(context["planning_root"]), state_values["approval_status"]),
        "threadId": thread_id,
        "assistantId": assistant["assistant_id"],
        "checkpointId": checkpoint_id_from_snapshot(snapshot),
        "resumeHandlePath": str(Path(context["runtime_root"]).resolve() / "resume-handle.json"),
    }


def command_status(args: argparse.Namespace, client: Any, load_resume_handle: Any) -> dict[str, Any]:
    context = resolve_context(args)
    resume_handle = load_resume_handle(context["project_root"], context["run_id"])
    payload = {"context": context, "handles": resume_handle.get("handles", {}), "serverUrl": DEFAULT_SERVER_URL}
    thread_states: dict[str, Any] = {}
    for graph_id, handle in (resume_handle.get("handles") or {}).items():
        try:
            snapshot = thread_snapshot(client, handle["thread_id"])
            thread_states[graph_id] = {
                "thread": snapshot["thread"],
                "state": snapshot["state"],
            }
        except Exception as exc:  # noqa: BLE001
            thread_states[graph_id] = {"error": str(exc)}
    payload["threads"] = thread_states
    return payload


def command_approve(args: argparse.Namespace, client: Any, planning_lib: Any, load_resume_handle: Any, write_resume_handle: Any, append_event: Any, write_runtime_exports: Any) -> dict[str, Any]:
    context = resolve_context(args)
    resume_handle = load_resume_handle(context["project_root"], context["run_id"])
    planning_handle = (resume_handle.get("handles") or {}).get("phase_stage_planning")
    if not planning_handle:
        raise ValueError("Planning handle not found. Run plan first.")
    planning_assistant = ensure_assistant(client, "phase_stage_planning")
    create_and_join_run(
        client,
        thread_id=planning_handle["thread_id"],
        assistant_id=planning_assistant["assistant_id"],
        command_payload={"resume": {"action": "approve"}},
    )
    planning_state = thread_snapshot(client, planning_handle["thread_id"])
    autorun_assistant = ensure_assistant(client, "phase_stage_autorun")
    autorun_handle = (resume_handle.get("handles") or {}).get("phase_stage_autorun", {})
    autorun_thread_id = autorun_handle.get("thread_id")
    if not autorun_thread_id:
        thread = client.threads.create(graph_id="phase_stage_autorun", metadata={"run_id": context["run_id"], "graph_id": "phase_stage_autorun"})
        autorun_thread_id = str(thread["thread_id"])
    create_and_join_run(
        client,
        thread_id=autorun_thread_id,
        assistant_id=autorun_assistant["assistant_id"],
        input_payload={
            "graph_id": "phase_stage_autorun",
            "assistant_id": autorun_assistant["assistant_id"],
            "thread_id": autorun_thread_id,
            "run_id": context["run_id"],
            "title": planning_state["state"]["values"]["title"],
            "project_root": context["project_root"],
            "planning_root": context["planning_root"],
            "runtime_root": context["runtime_root"],
        },
    )
    autorun_snapshot = thread_snapshot(client, autorun_thread_id)
    state_values = dict(autorun_snapshot["state"]["values"])
    state_values.update({"assistant_id": autorun_assistant["assistant_id"], "thread_id": autorun_thread_id})
    export_paths = write_runtime_exports(state_values, "phase_stage_autorun")
    resume_handle["handles"] = dict(resume_handle.get("handles") or {})
    resume_handle["handles"]["phase_stage_planning"] = {
        "graph_id": "phase_stage_planning",
        "assistant_id": planning_assistant["assistant_id"],
        "thread_id": planning_handle["thread_id"],
        "checkpoint_id": checkpoint_id_from_snapshot(planning_state),
        "status": planning_state["thread"]["status"],
        "updated_at": now_iso(),
    }
    resume_handle["handles"]["phase_stage_autorun"] = {
        "graph_id": "phase_stage_autorun",
        "assistant_id": autorun_assistant["assistant_id"],
        "thread_id": autorun_thread_id,
        "checkpoint_id": checkpoint_id_from_snapshot(autorun_snapshot),
        "status": autorun_snapshot["thread"]["status"],
        "updated_at": now_iso(),
    }
    resume_handle["active_graph"] = "phase_stage_autorun"
    resume_handle["updated_at"] = now_iso()
    write_resume_handle(context["project_root"], context["run_id"], resume_handle)
    append_event(context["project_root"], context["run_id"], "approve", {"thread_id": autorun_thread_id})
    return {
        "planning": planning_lib.export_planning_state(planning_lib.load_task_context(context["planning_root"]), "approved"),
        "autorun": {
            "threadId": autorun_thread_id,
            "assistantId": autorun_assistant["assistant_id"],
            "checkpointId": checkpoint_id_from_snapshot(autorun_snapshot),
            "status": autorun_snapshot["thread"]["status"],
            "state": state_values,
            "exports": export_paths,
        },
    }


def command_expand_phase(args: argparse.Namespace, client: Any, planning_lib: Any, load_resume_handle: Any, write_resume_handle: Any, append_event: Any) -> dict[str, Any]:
    context = resolve_context(args)
    resume_handle = load_resume_handle(context["project_root"], context["run_id"])
    planning_handle = (resume_handle.get("handles") or {}).get("phase_stage_planning")
    if not planning_handle:
        raise ValueError("Planning handle not found. Run plan first.")
    planning_assistant = ensure_assistant(client, "phase_stage_planning")
    snapshot = thread_snapshot(client, planning_handle["thread_id"])
    if snapshot["thread"]["status"] != "interrupted":
        create_and_join_run(
            client,
            thread_id=planning_handle["thread_id"],
            assistant_id=planning_assistant["assistant_id"],
            input_payload=planning_input_payload(
                planning_lib,
                context["planning_root"],
                planning_assistant["assistant_id"],
                planning_handle["thread_id"],
            ),
        )
    create_and_join_run(
        client,
        thread_id=planning_handle["thread_id"],
        assistant_id=planning_assistant["assistant_id"],
        command_payload={"resume": {"action": "expand_phase", "phase_id": args.phase_id}},
    )
    snapshot = thread_snapshot(client, planning_handle["thread_id"])
    resume_handle["handles"]["phase_stage_planning"]["checkpoint_id"] = checkpoint_id_from_snapshot(snapshot)
    resume_handle["handles"]["phase_stage_planning"]["status"] = snapshot["thread"]["status"]
    resume_handle["updated_at"] = now_iso()
    write_resume_handle(context["project_root"], context["run_id"], resume_handle)
    append_event(context["project_root"], context["run_id"], "expand_phase", {"phase_id": args.phase_id or "auto"})
    task_context = planning_lib.load_task_context(context["planning_root"])
    return planning_lib.export_planning_state(task_context, task_context["approvalStatus"])


def command_continue(args: argparse.Namespace, client: Any, planning_lib: Any, load_resume_handle: Any, write_resume_handle: Any, append_event: Any, write_runtime_exports: Any, is_resume: bool = False) -> dict[str, Any]:
    context = resolve_context(args)
    graph_id = args.graph_id
    resume_handle = load_resume_handle(context["project_root"], context["run_id"])
    assistant = ensure_assistant(client, graph_id)
    graph_handle = (resume_handle.get("handles") or {}).get(graph_id, {})
    thread_id = graph_handle.get("thread_id")
    input_payload = read_json(Path(args.input_json).resolve()) if args.input_json else None
    if not thread_id:
        if not input_payload:
            raise ValueError(f"No existing {graph_id} thread handle found; pass --input-json to start one.")
        thread = client.threads.create(graph_id=graph_id, metadata={"run_id": context["run_id"], "graph_id": graph_id})
        thread_id = str(thread["thread_id"])
        input_payload.update({"assistant_id": assistant["assistant_id"], "thread_id": thread_id, "run_id": context["run_id"]})
    command = None
    if args.executor_result_json:
        command = {"resume": read_json(Path(args.executor_result_json).resolve())}
    create_and_join_run(
        client,
        thread_id=thread_id,
        assistant_id=assistant["assistant_id"],
        input_payload=input_payload,
        command_payload=command,
    )
    snapshot = thread_snapshot(client, thread_id)
    state_values = dict(snapshot["state"]["values"])
    state_values.update(
        {
            "assistant_id": assistant["assistant_id"],
            "thread_id": thread_id,
            "project_root": context["project_root"],
            "planning_root": context["planning_root"],
            "runtime_root": context["runtime_root"],
            "run_id": context["run_id"],
        }
    )
    exports = write_runtime_exports(state_values, graph_id)
    resume_handle["handles"] = dict(resume_handle.get("handles") or {})
    resume_handle["handles"][graph_id] = {
        "graph_id": graph_id,
        "assistant_id": assistant["assistant_id"],
        "thread_id": thread_id,
        "checkpoint_id": checkpoint_id_from_snapshot(snapshot),
        "status": snapshot["thread"]["status"],
        "updated_at": now_iso(),
    }
    resume_handle["active_graph"] = graph_id
    resume_handle["updated_at"] = now_iso()
    write_resume_handle(context["project_root"], context["run_id"], resume_handle)
    append_event(context["project_root"], context["run_id"], "resume" if is_resume else "continue", {"graph_id": graph_id, "thread_id": thread_id})
    return {
        "graphId": graph_id,
        "threadId": thread_id,
        "assistantId": assistant["assistant_id"],
        "checkpointId": checkpoint_id_from_snapshot(snapshot),
        "status": snapshot["thread"]["status"],
        "state": state_values,
        "interrupts": snapshot["state"].get("interrupts", []),
        "exports": exports,
    }


def command_export(args: argparse.Namespace, client: Any, planning_lib: Any, load_resume_handle: Any, write_runtime_exports: Any) -> dict[str, Any]:
    context = resolve_context(args)
    graph_id = args.graph_id
    resume_handle = load_resume_handle(context["project_root"], context["run_id"])
    graph_handle = (resume_handle.get("handles") or {}).get(graph_id)
    if not graph_handle:
        raise ValueError(f"No handle found for graph {graph_id}")
    snapshot = thread_snapshot(client, graph_handle["thread_id"])
    state_values = dict(snapshot["state"]["values"])
    state_values.update(
        {
            "assistant_id": graph_handle["assistant_id"],
            "thread_id": graph_handle["thread_id"],
            "project_root": context["project_root"],
            "planning_root": context["planning_root"],
            "runtime_root": context["runtime_root"],
            "run_id": context["run_id"],
        }
    )
    exports = write_runtime_exports(state_values, graph_id)
    return {"graphId": graph_id, "exports": exports}


if __name__ == "__main__":
    raise SystemExit(main())
