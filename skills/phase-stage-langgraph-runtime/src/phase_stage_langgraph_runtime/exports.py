from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .io_utils import now_iso, render_template, write_json, write_text
from .models import ACLX_PROTOCOL_VERSION, ResumeHandle
from .planning import runtime_root_for


def runtime_paths(project_root: str | Path, run_id: str) -> dict[str, Path]:
    root = runtime_root_for(project_root, run_id)
    return {
        "root": root,
        "runtime_view": root / "runtime-view.aclx",
        "queue": root / "queue.md",
        "status": root / "status.json",
        "resume_handle": root / "resume-handle.json",
        "event_log": root / "event-log.jsonl",
    }


def write_runtime_exports(state: dict[str, Any], graph_id: str) -> dict[str, str]:
    paths = runtime_paths(state["project_root"], state["run_id"])
    paths["root"].mkdir(parents=True, exist_ok=True)

    queue_items = state.get("queue_items") or []
    queue_lines = "\n".join(f"{index}. {item}" for index, item in enumerate(queue_items, start=1)) or "1. none"
    write_text(
        paths["queue"],
        render_template(
            "runtime-queue.template.md",
            {
                "run_id": state["run_id"],
                "graph_id": graph_id,
                "queue_cursor": state.get("queue_cursor", 0),
                "current_stage_id": state.get("current_stage_id", "none"),
                "current_stage_path": state.get("current_stage_path", "none"),
                "stage_state": state.get("stage_state", "planned"),
                "queue_lines": queue_lines,
            },
        ),
    )
    write_text(
        paths["runtime_view"],
        render_template(
            "runtime-view.template.aclx",
            {
                "protocol_version": ACLX_PROTOCOL_VERSION,
                "run_id": state["run_id"],
                "title": state.get("title", "none"),
                "graph_id": graph_id,
                "assistant_id": state.get("assistant_id", "none"),
                "thread_id": state.get("thread_id", "none"),
                "runtime_mode": state.get("runtime_mode", "t0"),
                "project_root": state.get("project_root", "none"),
                "planning_root": state.get("planning_root", "none"),
                "runtime_root": paths["root"],
                "queue_items_json": json.dumps(queue_items, ensure_ascii=True),
                "queue_cursor": state.get("queue_cursor", 0),
                "current_phase_id": state.get("phase_id") or state.get("current_phase_id", "none"),
                "current_stage_id": state.get("current_stage_id", "none"),
                "current_stage_path": state.get("current_stage_path", "none"),
                "stage_state": state.get("stage_state", "planned"),
                "next_action": state.get("next_action", "none"),
                "blocker": state.get("blocker", "none"),
                "audit_pass_streak": state.get("audit_pass_streak", state.get("clean_pass_streak", 0)),
                "audit_fail_streak": state.get("audit_fail_streak", state.get("fail_streak", 0)),
                "latest_verification": state.get("latest_verification", "none"),
                "round": state.get("round", 0),
                "verification_phase": state.get("verification_phase", "none"),
                "checkpoint_id": state.get("checkpoint_id", "none"),
            },
        ),
    )
    write_json(
        paths["status"],
        {
            "runId": state["run_id"],
            "title": state.get("title", "none"),
            "graphId": graph_id,
            "assistantId": state.get("assistant_id", "none"),
            "threadId": state.get("thread_id", "none"),
            "runtimeMode": state.get("runtime_mode", "t0"),
            "queueCursor": state.get("queue_cursor", 0),
            "currentPhaseId": state.get("phase_id") or state.get("current_phase_id", "none"),
            "currentStageId": state.get("current_stage_id", "none"),
            "currentStagePath": state.get("current_stage_path", "none"),
            "stageState": state.get("stage_state", "planned"),
            "nextAction": state.get("next_action", "none"),
            "blocker": state.get("blocker", "none"),
            "auditPassStreak": state.get("audit_pass_streak", state.get("clean_pass_streak", 0)),
            "auditFailStreak": state.get("audit_fail_streak", state.get("fail_streak", 0)),
            "latestVerification": state.get("latest_verification", "none"),
            "updatedAt": now_iso(),
        },
    )
    return {key: str(value.resolve()) for key, value in paths.items()}


def write_resume_handle(project_root: str | Path, run_id: str, payload: ResumeHandle) -> str:
    paths = runtime_paths(project_root, run_id)
    paths["root"].mkdir(parents=True, exist_ok=True)
    write_json(paths["resume_handle"], payload)
    return str(paths["resume_handle"].resolve())


def load_resume_handle(project_root: str | Path, run_id: str) -> ResumeHandle:
    paths = runtime_paths(project_root, run_id)
    if not paths["resume_handle"].exists():
        return {
            "version": ACLX_PROTOCOL_VERSION,
            "server_url": "http://127.0.0.1:2024",
            "run_id": run_id,
            "project_root": str(Path(project_root).resolve()),
            "planning_root": str((Path(project_root).resolve() / "plans" / "phase-stage-langgraph" / run_id).resolve()),
            "runtime_root": str(paths["root"].resolve()),
            "active_graph": "phase_stage_planning",
            "updated_at": now_iso(),
            "handles": {},
        }
    from .io_utils import read_json

    return read_json(paths["resume_handle"])  # type: ignore[return-value]


def append_event(project_root: str | Path, run_id: str, event_type: str, payload: dict[str, Any]) -> str:
    paths = runtime_paths(project_root, run_id)
    paths["root"].mkdir(parents=True, exist_ok=True)
    record = {"ts": now_iso(), "type": event_type, "payload": payload}
    with paths["event_log"].open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return str(paths["event_log"].resolve())
