from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .exports import write_runtime_exports
from .io_utils import now_iso, write_json
from .models import AutorunState, PlanningState, VerificationLoopState
from . import planning as planning_lib


def _planning_state_updates(task_context: dict[str, Any], metadata: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    return {
        "graph_id": "phase_stage_planning",
        "assistant_id": base.get("assistant_id", ""),
        "thread_id": base.get("thread_id", ""),
        "run_id": task_context["runId"],
        "title": task_context["title"],
        "task": task_context["task"],
        "project_root": task_context["projectRoot"],
        "planning_root": task_context["planningRoot"],
        "runtime_root": task_context.get("runtimeRoot", metadata.get("runtimeRoot")),
        "generated_at": task_context["generatedAt"],
        "planning_mode": task_context["planningMode"],
        "runtime_mode": "t0",
        "success_criteria": task_context["successCriteria"],
        "constraints": task_context["constraints"],
        "scan": task_context["scan"],
        "phases": task_context["phases"],
        "approval_status": task_context["approvalStatus"],
        "current_phase_id": metadata["currentPhaseId"],
        "current_executable_phase_id": metadata["currentExecutablePhaseId"],
        "first_pending_phase_id": metadata["firstPendingPhaseId"],
        "ready_phase_ids": metadata["readyPhaseIds"],
        "pending_phase_ids": metadata["pendingPhaseIds"],
        "current_stage_queue": metadata["currentExecutableStages"],
    }


def _load_planning_from_disk(planning_root: str | Path, base: dict[str, Any]) -> dict[str, Any]:
    task_context, _ = planning_lib.load_planning_state(planning_root)
    metadata = planning_lib.export_planning_state(task_context, task_context["approvalStatus"])
    return _planning_state_updates(task_context, metadata, base)


def plan_scan_project(state: PlanningState) -> PlanningState:
    if state.get("project_root") and Path(state["planning_root"]).exists():
        return {}
    planning_root = state.get("planning_root") or str(planning_lib.planning_root_for(state["project_root"], state["run_id"]))
    runtime_root = state.get("runtime_root") or str(planning_lib.runtime_root_for(state["project_root"], state["run_id"]))
    return {
        "planning_root": planning_root,
        "runtime_root": runtime_root,
        "generated_at": state.get("generated_at", now_iso()),
        "runtime_mode": "t0",
    }


def plan_build_specs(state: PlanningState) -> PlanningState:
    if Path(state["planning_root"]).joinpath("task-context.json").exists():
        return _load_planning_from_disk(state["planning_root"], state)
    planning_lib.write_planning_bundle(
        project_root=state["project_root"],
        run_id=state["run_id"],
        title=state["title"],
        task_text=state["task"],
        success_criteria=list(state.get("success_criteria") or []),
        constraints=list(state.get("constraints") or []),
        planning_root=state["planning_root"],
    )
    return _load_planning_from_disk(state["planning_root"], state)


def plan_materialize(state: PlanningState) -> PlanningState:
    return state


def plan_export(state: PlanningState) -> PlanningState:
    planning_root = Path(state["planning_root"]).resolve()
    runtime_root = Path(state["runtime_root"]).resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    write_json(
        runtime_root / "status.json",
        {
            "runId": state["run_id"],
            "graphId": "phase_stage_planning",
            "planningRoot": str(planning_root),
            "approvalStatus": state["approval_status"],
            "currentPhaseId": state["current_phase_id"],
            "currentExecutablePhaseId": state["current_executable_phase_id"],
            "updatedAt": now_iso(),
        },
    )
    return {}


def plan_wait(state: PlanningState) -> PlanningState:
    resume_payload = interrupt(
        {
            "kind": "planning_command",
            "assistant_id": state.get("assistant_id", ""),
            "thread_id": state.get("thread_id", ""),
            "run_id": state["run_id"],
            "runtime_mode": "t0",
            "phase_id": state["current_phase_id"],
            "stage_id": "planning",
            "round": 0,
            "artifact_refs": {
                "planning_root": state["planning_root"],
                "planning_state": str(Path(state["planning_root"]).resolve() / "planning-state.aclx"),
                "protocol": str(Path(state["planning_root"]).resolve() / "autorun-protocol.md"),
            },
            "state_delta": {
                "approval_status": state["approval_status"],
                "ready_phase_ids": state["ready_phase_ids"],
                "pending_phase_ids": state["pending_phase_ids"],
            },
            "executor_packet": {
                "allowed_actions": ["approve", "expand_phase", "cancel"],
                "first_pending_phase_id": state["first_pending_phase_id"],
            },
        }
    )
    return {"last_action": dict(resume_payload or {})}


def plan_apply_action(state: PlanningState) -> PlanningState:
    action = dict(state.get("last_action") or {})
    command = action.get("action", "none")
    planning_root = Path(state["planning_root"]).resolve()
    task_context, _ = planning_lib.load_planning_state(planning_root)
    if command == "approve":
        task_context = planning_lib.mark_approved(task_context)
        write_json(planning_root / "task-context.json", task_context)
        planning_lib.write_phase_index(planning_root / "phase-index.md", planning_root, task_context)
        planning_lib.write_planning_state(planning_lib.planning_state_path(planning_root), planning_root, task_context)
        planning_lib.write_autorun_protocol(planning_root / "autorun-protocol.md", planning_root, task_context)
        return _planning_state_updates(
            task_context,
            planning_lib.export_planning_state(task_context, task_context["approvalStatus"]),
            state,
        )
    if command == "expand_phase":
        phase_id = action.get("phase_id") or state["first_pending_phase_id"]
        planning_lib.expand_phase(planning_root=planning_root, phase_id=phase_id)
        return _load_planning_from_disk(planning_root, state)
    if command == "cancel":
        task_context["approvalStatus"] = "cancelled"
        write_json(planning_root / "task-context.json", task_context)
        planning_lib.write_phase_index(planning_root / "phase-index.md", planning_root, task_context)
        planning_lib.write_planning_state(planning_lib.planning_state_path(planning_root), planning_root, task_context)
        planning_lib.write_autorun_protocol(planning_root / "autorun-protocol.md", planning_root, task_context)
        return _planning_state_updates(
            task_context,
            planning_lib.export_planning_state(task_context, task_context["approvalStatus"]),
            state,
        )
    return {}


def plan_route_after_action(state: PlanningState) -> str:
    if state.get("approval_status") in {"approved", "cancelled"}:
        return END
    return "export_planning_view"


def verification_prepare(state: VerificationLoopState) -> VerificationLoopState:
    return {
        "graph_id": "generator_critic_loop",
        "runtime_mode": "t3",
        "round": state.get("round", 1),
        "verification_phase": state.get("verification_phase", "dispatch_critic"),
        "next_dispatch_role": state.get("next_dispatch_role", "critic"),
        "clean_pass_streak": state.get("clean_pass_streak", 0),
        "fail_streak": state.get("fail_streak", 0),
        "repeated_issue_count": state.get("repeated_issue_count", 0),
        "strategy_change_required": state.get("strategy_change_required", False),
    }


def verification_request(state: VerificationLoopState) -> VerificationLoopState:
    role = state.get("next_dispatch_role", "critic")
    packet = {
        "kind": f"{role}_request",
        "assistant_id": state.get("assistant_id", ""),
        "thread_id": state.get("thread_id", ""),
        "run_id": state["run_id"],
        "runtime_mode": "t3",
        "phase_id": state.get("phase_id", "verification"),
        "stage_id": state.get("stage_id", "verification"),
        "round": state.get("round", 1),
        "artifact_refs": {
            "planning_root": state.get("planning_root", ""),
            "runtime_root": state.get("runtime_root", ""),
        },
        "state_delta": {
            "clean_pass_streak": state.get("clean_pass_streak", 0),
            "fail_streak": state.get("fail_streak", 0),
            "last_verdict": state.get("last_verdict", "none"),
        },
        "executor_packet": {
            "role": role,
            "current_execution_plan_id": state.get("current_execution_plan_id", state.get("stage_id", "none")),
            "current_repair_plan_id": state.get("current_repair_plan_id", "none"),
            "release_candidate_id": state.get("release_candidate_id", state.get("latest_verification", "none")),
        },
    }
    result = interrupt(packet)
    return {
        "last_interrupt": packet,
        "latest_executor_result": dict(result or {}),
    }


def verification_reduce(state: VerificationLoopState) -> VerificationLoopState:
    result = dict(state.get("latest_executor_result") or {})
    role = state.get("next_dispatch_role", "critic")
    verdict = str(result.get("verdict_or_status") or "").upper()
    evidence = list(result.get("verification_evidence") or [])
    delta = dict(result.get("state_delta") or {})
    issue_key = str(delta.get("issue_key") or result.get("blocker_or_none") or verdict or "none")
    updates: dict[str, Any] = {
        "latest_verification": evidence[-1] if evidence else state.get("latest_verification", "none"),
    }
    if role == "critic":
        if verdict == "PASS":
            clean_pass_streak = int(state.get("clean_pass_streak", 0)) + 1
            updates.update(
                {
                    "clean_pass_streak": clean_pass_streak,
                    "fail_streak": 0,
                    "last_verdict": "PASS",
                    "next_dispatch_role": "critic",
                    "verification_phase": "terminal_accept" if clean_pass_streak >= 5 else "dispatch_critic",
                    "round": int(state.get("round", 1)) + 1,
                }
            )
        else:
            fail_streak = int(state.get("fail_streak", 0)) + 1
            repeated_count = int(state.get("repeated_issue_count", 0)) + 1 if issue_key == state.get("repeated_issue_key") else 1
            strategy_change = repeated_count >= 2
            updates.update(
                {
                    "clean_pass_streak": 0,
                    "fail_streak": fail_streak,
                    "last_verdict": "FAIL",
                    "next_dispatch_role": "refiner",
                    "verification_phase": "terminal_fail" if fail_streak >= 10 else "dispatch_refiner",
                    "repeated_issue_key": issue_key,
                    "repeated_issue_count": repeated_count,
                    "strategy_change_required": strategy_change,
                    "blocker": "strategy_change_required" if strategy_change else state.get("blocker", "none"),
                }
            )
    elif role == "refiner":
        required = ["failure_diagnosis", "target_files", "edit_actions", "verification_steps", "blockers"]
        plan_complete = bool(delta.get("plan_complete", all(key in delta for key in required)))
        updates.update(
            {
                "current_repair_plan_id": str(delta.get("plan_id", f"{state.get('stage_id', 'stage')}-repair-{state.get('round', 1)}")),
                "next_dispatch_role": "generator" if plan_complete else "refiner",
                "verification_phase": "dispatch_generator" if plan_complete else "dispatch_refiner",
            }
        )
    else:
        updates.update(
            {
                "release_candidate_id": str(delta.get("candidate_id", result.get("summary") or state.get("release_candidate_id", "none"))),
                "current_execution_plan_id": str(delta.get("execution_plan_id", state.get("current_execution_plan_id", state.get("stage_id", "none")))),
                "next_dispatch_role": "critic",
                "verification_phase": "dispatch_critic",
                "round": int(state.get("round", 1)) + 1,
                "blocker": result.get("blocker_or_none", "none"),
            }
        )
    return updates


def verification_route(state: VerificationLoopState) -> str:
    if state.get("verification_phase") in {"terminal_accept", "terminal_fail"}:
        return END
    return "request_verification_action"


def bootstrap_from_plan(state: AutorunState) -> AutorunState:
    task_context = planning_lib.load_task_context(state["planning_root"])
    if state.get("queue_items") and not (
        state.get("stage_state") == "blocked" and state.get("blocker") == "missing_plan"
    ):
        return {}
    if state.get("queue_items") and state.get("stage_state") == "blocked" and state.get("blocker") == "missing_plan":
        boundary = planning_lib.resolve_phase_boundary(task_context, state.get("current_stage_path"))
        if boundary and boundary.get("transition") == "advance_to_ready_stage":
            return {
                "queue_items": boundary["queue_items"],
                "queue_cursor": boundary["queue_cursor"],
                "current_stage_path": boundary["current_stage_path"],
                "current_stage_id": boundary["current_stage_id"],
                "stage_state": "planned",
                "next_action": "request_stage_execution",
                "blocker": "none",
            }
    queue_items = planning_lib.flatten_ready_stage_paths(task_context)
    if not queue_items:
        return {
            "stage_state": "blocked",
            "blocker": "missing_plan",
            "next_action": "expand_phase_plan",
            "queue_items": [],
            "queue_cursor": 0,
        }
    current_stage_path = queue_items[0]
    return {
        "graph_id": "phase_stage_autorun",
        "runtime_mode": "t0",
        "queue_items": queue_items,
        "queue_cursor": 0,
        "current_stage_id": Path(current_stage_path).stem,
        "current_stage_path": current_stage_path,
        "stage_state": "planned",
        "next_action": "request_stage_execution",
        "blocker": "none",
        "audit_pass_streak": 0,
        "audit_fail_streak": 0,
        "latest_verification": "none",
        "phase_id": task_context.get("currentPhaseId", "none"),
        "planning_state_path": str(Path(state["planning_root"]).resolve() / "planning-state.aclx"),
        "protocol_path": str(Path(state["planning_root"]).resolve() / "autorun-protocol.md"),
    }


def preflight_current_stage(state: AutorunState) -> AutorunState:
    current_stage_path = state.get("current_stage_path")
    if current_stage_path and Path(current_stage_path).exists():
        return {"blocker": state.get("blocker", "none")}
    return {
        "stage_state": "blocked",
        "blocker": "missing_plan",
        "next_action": "expand_phase_plan",
    }


def export_runtime_view(state: AutorunState) -> AutorunState:
    write_runtime_exports(state, "phase_stage_autorun")
    return {}


def autorun_route(state: AutorunState) -> str:
    if state.get("stage_state") == "blocked" or state.get("next_action") == "complete_run":
        return END
    if state.get("stage_state") == "planned":
        return "request_executor_action"
    if state.get("stage_state") == "build_verified":
        return "generator_critic_loop"
    if state.get("stage_state") == "post_repair_verified":
        return "advance_or_block"
    return END


def request_executor_action(state: AutorunState) -> AutorunState:
    packet = {
        "kind": "stage_execution_request",
        "assistant_id": state.get("assistant_id", ""),
        "thread_id": state.get("thread_id", ""),
        "run_id": state["run_id"],
        "runtime_mode": state.get("runtime_mode", "t0"),
        "phase_id": state.get("phase_id", "none"),
        "stage_id": state.get("current_stage_id", "none"),
        "round": state.get("round", 0),
        "artifact_refs": {
            "planning_state": state.get("planning_state_path", ""),
            "autorun_protocol": state.get("protocol_path", ""),
            "stage_plan": state.get("current_stage_path", ""),
            "runtime_view": str(Path(state["runtime_root"]).resolve() / "runtime-view.aclx"),
        },
        "state_delta": {
            "queue_cursor": state.get("queue_cursor", 0),
            "stage_state": state.get("stage_state", "planned"),
        },
        "executor_packet": planning_lib.stage_plan_metadata(state.get("current_stage_path")),
    }
    result = interrupt(packet)
    return {
        "last_interrupt": packet,
        "latest_executor_result": dict(result or {}),
    }


def reduce_executor_result(state: AutorunState) -> AutorunState:
    result = dict(state.get("latest_executor_result") or {})
    blocker = str(result.get("blocker_or_none") or "none")
    evidence = list(result.get("verification_evidence") or [])
    if blocker not in ("", "none"):
        return {
            "stage_state": "blocked",
            "blocker": blocker,
            "next_action": "report_blocker",
            "latest_verification": evidence[-1] if evidence else state.get("latest_verification", "none"),
        }
    return {
        "stage_state": "build_verified",
        "next_action": "start_audit",
        "blocker": "none",
        "latest_verification": evidence[-1] if evidence else state.get("latest_verification", "build_verified"),
        "release_candidate_id": str(result.get("summary") or state.get("current_stage_id", "candidate")),
        "current_execution_plan_id": state.get("current_stage_id", "none"),
        "verification_phase": "dispatch_critic",
        "next_dispatch_role": "critic",
        "clean_pass_streak": 0,
        "fail_streak": 0,
        "round": 1,
    }


def finalize_verification(state: AutorunState) -> AutorunState:
    if state.get("verification_phase") == "terminal_accept":
        return {
            "stage_state": "post_repair_verified",
            "next_action": "advance_stage",
            "blocker": "none",
            "audit_pass_streak": state.get("clean_pass_streak", 0),
            "audit_fail_streak": state.get("fail_streak", 0),
        }
    blocker = "strategy_change_required" if state.get("strategy_change_required") else state.get("blocker", "unresolved_contract")
    return {
        "stage_state": "blocked",
        "blocker": blocker,
        "next_action": "report_blocker",
        "audit_pass_streak": state.get("clean_pass_streak", 0),
        "audit_fail_streak": state.get("fail_streak", 0),
    }


def advance_or_block(state: AutorunState) -> AutorunState:
    task_context = planning_lib.load_task_context(state["planning_root"])
    boundary = planning_lib.resolve_phase_boundary(task_context, state.get("current_stage_path"))
    if boundary and boundary.get("transition") == "advance_to_ready_stage":
        return {
            "queue_items": boundary["queue_items"],
            "queue_cursor": boundary["queue_cursor"],
            "current_stage_path": boundary["current_stage_path"],
            "current_stage_id": boundary["current_stage_id"],
            "stage_state": "planned",
            "next_action": "request_stage_execution",
            "blocker": "none",
            "audit_pass_streak": 0,
            "audit_fail_streak": 0,
            "clean_pass_streak": 0,
            "fail_streak": 0,
            "round": 0,
        }
    if boundary and boundary.get("transition") == "block_for_expand":
        return {
            "stage_state": "blocked",
            "blocker": "missing_plan",
            "next_action": "expand_phase_plan",
            "latest_verification": boundary.get("phase_id", "missing_plan"),
        }
    return {
        "stage_state": "done",
        "next_action": "complete_run",
        "blocker": "none",
    }


planning_builder = StateGraph(PlanningState)
planning_builder.add_node("scan_project", plan_scan_project)
planning_builder.add_node("build_phase_specs", plan_build_specs)
planning_builder.add_node("materialize_plan_files", plan_materialize)
planning_builder.add_node("export_planning_view", plan_export)
planning_builder.add_node("await_approval_or_expand", plan_wait)
planning_builder.add_node("apply_planning_action", plan_apply_action)
planning_builder.add_edge(START, "scan_project")
planning_builder.add_edge("scan_project", "build_phase_specs")
planning_builder.add_edge("build_phase_specs", "materialize_plan_files")
planning_builder.add_edge("materialize_plan_files", "export_planning_view")
planning_builder.add_edge("export_planning_view", "await_approval_or_expand")
planning_builder.add_edge("await_approval_or_expand", "apply_planning_action")
planning_builder.add_conditional_edges("apply_planning_action", plan_route_after_action)
phase_stage_planning_graph = planning_builder.compile(name="Phase Stage Planning")


verification_builder = StateGraph(VerificationLoopState)
verification_builder.add_node("prepare_verification", verification_prepare)
verification_builder.add_node("request_verification_action", verification_request)
verification_builder.add_node("reduce_verification_result", verification_reduce)
verification_builder.add_edge(START, "prepare_verification")
verification_builder.add_edge("prepare_verification", "request_verification_action")
verification_builder.add_edge("request_verification_action", "reduce_verification_result")
verification_builder.add_conditional_edges("reduce_verification_result", verification_route)
generator_critic_loop_graph = verification_builder.compile(name="Generator Critic Loop")


autorun_builder = StateGraph(AutorunState)
autorun_builder.add_node("bootstrap_from_plan", bootstrap_from_plan)
autorun_builder.add_node("preflight_current_stage", preflight_current_stage)
autorun_builder.add_node("export_runtime_view", export_runtime_view)
autorun_builder.add_node("request_executor_action", request_executor_action)
autorun_builder.add_node("reduce_executor_result", reduce_executor_result)
autorun_builder.add_node("generator_critic_loop", generator_critic_loop_graph)
autorun_builder.add_node("finalize_verification", finalize_verification)
autorun_builder.add_node("advance_or_block", advance_or_block)
autorun_builder.add_edge(START, "bootstrap_from_plan")
autorun_builder.add_edge("bootstrap_from_plan", "preflight_current_stage")
autorun_builder.add_edge("preflight_current_stage", "export_runtime_view")
autorun_builder.add_conditional_edges("export_runtime_view", autorun_route)
autorun_builder.add_edge("request_executor_action", "reduce_executor_result")
autorun_builder.add_edge("reduce_executor_result", "export_runtime_view")
autorun_builder.add_edge("generator_critic_loop", "finalize_verification")
autorun_builder.add_edge("finalize_verification", "export_runtime_view")
autorun_builder.add_edge("advance_or_block", "export_runtime_view")
phase_stage_autorun_graph = autorun_builder.compile(name="Phase Stage Autorun")
