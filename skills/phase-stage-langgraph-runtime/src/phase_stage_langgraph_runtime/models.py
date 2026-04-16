from __future__ import annotations

from typing import Any, Literal

from typing_extensions import TypedDict


ACLX_PROTOCOL_VERSION = "phase-stage-langgraph/codex-v2"
PLANNING_PROTOCOL_VERSION = "phase-stage-planning-langgraph/codex-v2"
RUNTIME_PROTOCOL_VERSION = "phase-stage-runtime-langgraph/codex-v2"

GraphId = Literal[
    "phase_stage_planning",
    "phase_stage_autorun",
    "generator_critic_loop",
]
RuntimeMode = Literal["t0", "t3"]
StageState = Literal[
    "planned",
    "implementing",
    "build_verified",
    "audit_running",
    "repairing",
    "post_repair_verified",
    "done",
    "blocked",
]
Blocker = Literal[
    "none",
    "missing_plan",
    "missing_tool",
    "destructive_action",
    "conflicting_state",
    "unresolved_contract",
    "strategy_change_required",
]
VerificationPhase = Literal[
    "dispatch_critic",
    "await_critic",
    "dispatch_refiner",
    "await_refiner",
    "dispatch_generator",
    "await_generator",
    "terminal_accept",
    "terminal_fail",
]


class ExecutorInterrupt(TypedDict, total=False):
    kind: str
    assistant_id: str
    thread_id: str
    run_id: str
    runtime_mode: RuntimeMode
    phase_id: str
    stage_id: str
    round: int
    artifact_refs: dict[str, str]
    state_delta: dict[str, Any]
    executor_packet: dict[str, Any]


class ExecutorResult(TypedDict, total=False):
    kind: str
    summary: str
    changed_files: list[str]
    verification_evidence: list[str]
    verdict_or_status: str
    blocker_or_none: str
    recommended_next_action: str
    state_delta: dict[str, Any]


class ResumeGraphHandle(TypedDict, total=False):
    graph_id: GraphId
    assistant_id: str
    thread_id: str
    checkpoint_id: str
    status: str
    updated_at: str


class ResumeHandle(TypedDict, total=False):
    version: str
    server_url: str
    run_id: str
    project_root: str
    planning_root: str
    runtime_root: str
    active_graph: str
    updated_at: str
    handles: dict[str, ResumeGraphHandle]


class PlanningState(TypedDict, total=False):
    graph_id: GraphId
    assistant_id: str
    thread_id: str
    run_id: str
    title: str
    task: str
    project_root: str
    planning_root: str
    runtime_root: str
    generated_at: str
    planning_mode: str
    runtime_mode: RuntimeMode
    success_criteria: list[str]
    constraints: list[str]
    scan: dict[str, Any]
    phases: list[dict[str, Any]]
    approval_status: str
    current_phase_id: str
    current_executable_phase_id: str
    first_pending_phase_id: str
    ready_phase_ids: list[str]
    pending_phase_ids: list[str]
    current_stage_queue: list[str]
    last_action: dict[str, Any]
    last_interrupt: ExecutorInterrupt
    last_error: str


class VerificationLoopState(TypedDict, total=False):
    graph_id: GraphId
    assistant_id: str
    thread_id: str
    run_id: str
    runtime_mode: RuntimeMode
    phase_id: str
    stage_id: str
    round: int
    verification_phase: VerificationPhase
    release_candidate_id: str
    current_execution_plan_id: str
    current_repair_plan_id: str
    issue_ledger_id: str
    clean_pass_streak: int
    fail_streak: int
    repeated_issue_key: str
    repeated_issue_count: int
    last_verdict: str
    next_dispatch_role: str
    strategy_change_required: bool
    latest_verification: str
    latest_executor_result: ExecutorResult
    last_interrupt: ExecutorInterrupt
    blocker: str


class AutorunState(VerificationLoopState, total=False):
    title: str
    project_root: str
    planning_root: str
    runtime_root: str
    queue_items: list[str]
    queue_cursor: int
    current_stage_id: str
    current_stage_path: str
    stage_state: StageState
    next_action: str
    blocker: str
    audit_pass_streak: int
    audit_fail_streak: int
    current_phase_id: str
    current_phase_title: str
    planning_state_path: str
    protocol_path: str
    queue_path: str
    status_path: str
    runtime_view_path: str
    last_error: str
