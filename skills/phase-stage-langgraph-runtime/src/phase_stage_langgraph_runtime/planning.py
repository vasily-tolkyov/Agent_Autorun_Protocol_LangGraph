from __future__ import annotations

import contextlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SCRIPT_DIR / "templates"
PLANNING_STATE_PATH_RE = re.compile(r"^planningStatePath:\s*(.+?)\s*$", re.MULTILINE)
PLANNING_PROTOCOL_VERSION = "phase-stage-planning-langgraph/codex-v2"
JSON_BLOCK_RE = re.compile(r"```json autorun-metadata\s*(\{.*?\})\s*```", re.DOTALL)
WORKSTREAM_SPLIT_RE = re.compile(r"(?:\n+|[；;]+|\s+并且\s+|\s+以及\s+|\s+同时\s+|\s+and\s+)", re.IGNORECASE)
NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def planning_root_for(project_root: str | Path, run_id: str) -> Path:
    return Path(project_root).resolve() / "plans" / "phase-stage-langgraph" / run_id


def runtime_root_for(project_root: str | Path, run_id: str) -> Path:
    return Path(project_root).resolve() / ".codex" / "phase-stage-langgraph" / run_id


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    temp_file = Path(temp_path)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temp_file, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            temp_file.unlink()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def read_aclx(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in raw_line:
            raise ValueError(f"Invalid ACL-X line in {path}: {raw_line}")
        key, value = raw_line.split("=", 1)
        entries[key.strip()] = value.strip()
    return entries


def render_template(name: str, mapping: dict[str, Any]) -> str:
    content = read_text(TEMPLATES_DIR / name)
    for key, value in mapping.items():
        content = content.replace(f"{{{{{key}}}}}", stringify(value))
    return content


def stringify(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, (list, tuple)):
        return "\n".join(str(item) for item in value)
    if value is None:
        return "none"
    return str(value)


def relative_to(base: Path, target: Path) -> str:
    return str(target.resolve().relative_to(base.resolve())).replace("\\", "/")


def resolve_from(base: Path, raw_path: str | None) -> str | None:
    if raw_path in (None, "", "none"):
        return None
    candidate = Path(raw_path.strip("`"))
    if candidate.is_absolute():
        return str(candidate.resolve())
    return str((base / candidate).resolve())


def parse_json_value(raw_value: str | None, default: Any) -> Any:
    if raw_value in (None, "", "none"):
        return default
    return json.loads(raw_value)


def summarize_line(text: str, max_chars: int = 100) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def slugify(text: str, fallback: str) -> str:
    ascii_only = text.lower().encode("ascii", "ignore").decode("ascii")
    slug = NON_ALNUM_RE.sub("-", ascii_only).strip("-")
    return slug or fallback


def format_bullets(items: list[str]) -> str:
    cleaned = [item for item in items if item]
    return "\n".join(f"- {item}" for item in cleaned) if cleaned else "- none"


def format_numbered(items: list[str]) -> str:
    cleaned = [item for item in items if item]
    return "\n".join(f"{index}. {item}" for index, item in enumerate(cleaned, start=1)) if cleaned else "1. none"


def shorten_paths(paths: list[str], root: Path) -> list[str]:
    shortened: list[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        try:
            shortened.append(relative_to(root, path))
        except ValueError:
            shortened.append(str(path))
    return shortened


def phase_by_id(phases: list[dict[str, Any]], phase_id: str | None) -> dict[str, Any] | None:
    if not phase_id:
        return None
    return next((phase for phase in phases if phase["id"] == phase_id), None)


def first_ready_phase(phases: list[dict[str, Any]]) -> dict[str, Any] | None:
    for phase in phases:
        if phase["detailStatus"] == "ready" and phase.get("stageFiles"):
            return phase
    return None


def _dedupe_paths(candidates: list[Path], limit: int, directories_only: bool = False) -> list[Path]:
    results: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate.exists():
            continue
        if directories_only and not candidate.is_dir():
            continue
        if not directories_only and candidate.is_dir() and candidate.name != "workflows":
            continue
        key = str(candidate.resolve())
        if key in seen:
            continue
        seen.add(key)
        results.append(candidate.resolve())
        if len(results) >= limit:
            break
    return results


def scan_project(project_root: str | Path) -> dict[str, Any]:
    root = Path(project_root).resolve()
    docs = _dedupe_paths(
        [*root.glob("README*"), *root.glob("docs/**/*.md"), *root.glob("spec/**/*.md"), *root.glob("plans/**/*.md")],
        limit=24,
    )
    manifests = _dedupe_paths(
        [
            root / "package.json",
            root / "pyproject.toml",
            root / "requirements.txt",
            root / "Cargo.toml",
            root / "go.mod",
            root / "pom.xml",
            root / "build.gradle",
            root / "build.gradle.kts",
            root / "Makefile",
            root / ".github" / "workflows",
        ],
        limit=20,
    )
    source_dirs = _dedupe_paths(
        [root / name for name in ("src", "app", "lib", "packages", "services", "tests", "docs")],
        limit=16,
        directories_only=True,
    )
    manifest_names = {path.name for path in manifests}
    stack_labels: list[str] = []
    if "package.json" in manifest_names:
        stack_labels.append("node-js")
    if "pyproject.toml" in manifest_names or "requirements.txt" in manifest_names:
        stack_labels.append("python")
    if "Cargo.toml" in manifest_names:
        stack_labels.append("rust")
    if "go.mod" in manifest_names:
        stack_labels.append("go")
    if "pom.xml" in manifest_names or "build.gradle" in manifest_names or "build.gradle.kts" in manifest_names:
        stack_labels.append("jvm")
    if not stack_labels:
        stack_labels.append("unknown-stack")
    build_signals: list[str] = []
    if "package.json" in manifest_names:
        build_signals.append("npm run build")
    if "pyproject.toml" in manifest_names:
        build_signals.append("python -m pytest")
    if "requirements.txt" in manifest_names and "python -m pytest" not in build_signals:
        build_signals.append("pytest")
    if "Cargo.toml" in manifest_names:
        build_signals.append("cargo build")
    if "go.mod" in manifest_names:
        build_signals.append("go build ./...")
    if not build_signals:
        build_signals.append("project-specific build check")
    test_signals: list[str] = []
    if "package.json" in manifest_names:
        test_signals.append("npm test")
    if "pyproject.toml" in manifest_names or "requirements.txt" in manifest_names:
        test_signals.append("pytest")
    if "Cargo.toml" in manifest_names:
        test_signals.append("cargo test")
    if "go.mod" in manifest_names:
        test_signals.append("go test ./...")
    if not test_signals:
        test_signals.append("task-specific verification run")
    return {
        "projectRoot": str(root),
        "docs": [str(path) for path in docs],
        "manifests": [str(path) for path in manifests],
        "sourceDirs": [str(path) for path in source_dirs],
        "stackLabels": stack_labels,
        "buildSignals": build_signals,
        "testSignals": test_signals,
    }


def extract_workstreams(task_text: str) -> list[str]:
    lines = [line.strip(" -*\t") for line in task_text.splitlines() if line.strip()]
    if len(lines) >= 2:
        return _dedupe_strings(lines)
    parts = [part.strip(" .。") for part in WORKSTREAM_SPLIT_RE.split(task_text) if part.strip(" .。")]
    return _dedupe_strings(parts) or [summarize_line(task_text, 160)]


def build_phase_specs(workstreams: list[str]) -> list[dict[str, Any]]:
    phases = [
        {
            "id": "phase-01-scope-and-surface-lock",
            "title": "Scope and surface lock",
            "type": "foundation",
            "objective": "Lock task scope, impacted surfaces, and verification baseline before broad implementation starts.",
            "detailStatus": "pending",
            "deliverables": ["Confirmed scope", "Impacted surfaces", "Verification baseline"],
            "exitCriteria": ["Scope is explicit", "Surfaces are mapped", "Verification baseline is ready"],
            "dependsOn": [],
        }
    ]
    previous_phase_id = phases[0]["id"]
    for index, workstream in enumerate(workstreams, start=1):
        phase_number = index + 1
        phases.append(
            {
                "id": f"phase-{phase_number:02d}-{slugify(f'workstream-{index}', f'workstream-{index}')}",
                "title": f"Workstream {index:02d}",
                "type": "implementation",
                "objective": workstream,
                "detailStatus": "pending",
                "deliverables": ["Implemented changes", "Integrated updates", "Verification evidence"],
                "exitCriteria": ["Workstream objective is implemented", "Interfaces stay consistent", "Verification passes"],
                "dependsOn": [previous_phase_id],
            }
        )
        previous_phase_id = phases[-1]["id"]
    phases.append(
        {
            "id": f"phase-{len(phases) + 1:02d}-verification-and-handoff",
            "title": "Verification and handoff",
            "type": "verification",
            "objective": "Run final verification, hardening, and handoff checks across the completed task.",
            "detailStatus": "pending",
            "deliverables": ["Final verification evidence", "Closed findings", "Handoff-ready state"],
            "exitCriteria": ["Task-level verification is complete", "Findings are closed or documented", "Task is safe to hand off"],
            "dependsOn": [previous_phase_id],
        }
    )
    return phases


def build_stage_outline(phase: dict[str, Any]) -> list[str]:
    if phase["type"] == "foundation":
        return ["Validate task scope and acceptance", "Map impacted implementation surfaces", "Prepare execution baseline"]
    if phase["type"] == "verification":
        return ["Run final verification", "Close or document findings", "Prepare handoff-ready completion state"]
    return ["Prepare workstream implementation slice", "Implement and integrate workstream changes", "Verify the workstream and close findings"]


def build_stage_specs(phase: dict[str, Any], task_text: str, scan: dict[str, Any]) -> list[dict[str, Any]]:
    root = Path(scan["projectRoot"])
    if phase["type"] == "foundation":
        return [
            {"id": "stage-01-validate-task-scope", "fileName": "stage-01-validate-task-scope.md", "title": "Validate task scope", "objective": "Restate the task, constraints, and success criteria in project terms.", "inputs": ["User task description", *shorten_paths(scan["docs"], root)[:3]], "changeScope": ["Planning and scoping only"], "dependencies": ["none"], "acceptanceCriteria": ["Task objective is unambiguous", "Constraints are explicit", "Success criteria are locked"], "verificationSteps": ["Cross-check the task against project docs", "Confirm the scope is specific enough for implementation"], "notes": [summarize_line(task_text, 140)]},
            {"id": "stage-02-map-implementation-surface", "fileName": "stage-02-map-implementation-surface.md", "title": "Map implementation surface", "objective": "Identify the code, config, and verification surfaces the task is likely to touch.", "inputs": [*shorten_paths(scan["manifests"], root)[:4], *shorten_paths(scan["sourceDirs"], root)[:4]], "changeScope": ["Implementation surface discovery"], "dependencies": ["stage-01-validate-task-scope"], "acceptanceCriteria": ["Impacted surfaces are identified", "Build and dependency risks are visible"], "verificationSteps": ["Compare mapped surfaces to the task objective", "Check that each surface has a verification path"], "notes": ["Use these mapped surfaces to shape downstream workstreams."]},
            {"id": "stage-03-prepare-execution-baseline", "fileName": "stage-03-prepare-execution-baseline.md", "title": "Prepare execution baseline", "objective": "Prepare the build and test baseline that downstream stages must satisfy.", "inputs": [*scan["buildSignals"], *scan["testSignals"]], "changeScope": ["Verification baseline"], "dependencies": ["stage-02-map-implementation-surface"], "acceptanceCriteria": ["Build and test expectations are explicit", "Execution can proceed without baseline ambiguity"], "verificationSteps": ["Check that the baseline covers mapped surfaces", "Confirm the baseline is usable in audit gates"], "notes": ["This stage prepares execution but does not implement the feature."]},
        ]
    if phase["type"] == "verification":
        return [
            {"id": "stage-01-run-final-verification", "fileName": "stage-01-run-final-verification.md", "title": "Run final verification", "objective": "Run final task-level verification across the completed work.", "inputs": [*scan["buildSignals"], *scan["testSignals"]], "changeScope": ["Final build, test, and regression checks"], "dependencies": phase["dependsOn"] or ["all implementation phases"], "acceptanceCriteria": ["Final verification covers the task surface", "Regressions are caught before handoff"], "verificationSteps": ["Execute the final verification matrix", "Capture evidence for acceptance checks"], "notes": ["Do not introduce new feature scope here."]},
            {"id": "stage-02-close-findings-and-handoff", "fileName": "stage-02-close-findings-and-handoff.md", "title": "Close findings and handoff", "objective": "Resolve remaining findings or document residual risk, then prepare handoff.", "inputs": ["Final verification evidence", "Outstanding finding list"], "changeScope": ["Hardening and handoff readiness"], "dependencies": ["stage-01-run-final-verification"], "acceptanceCriteria": ["Critical and major findings are closed or documented", "Task is safe to hand off"], "verificationSteps": ["Review findings against acceptance criteria", "Confirm the result is handoff-ready"], "notes": ["Keep this stage focused on closure readiness."]},
        ]
    summary = summarize_line(phase["objective"], 120)
    return [
        {"id": "stage-01-prepare-workstream-scope", "fileName": "stage-01-prepare-workstream-scope.md", "title": "Prepare workstream scope", "objective": f"Translate the workstream objective into a concrete implementation slice: {summary}", "inputs": [summary, *shorten_paths(scan["sourceDirs"], root)[:4]], "changeScope": ["Workstream-specific code, config, and tests"], "dependencies": phase["dependsOn"] or ["foundation phase complete"], "acceptanceCriteria": ["Implementation slice is concrete and bounded", "Dependencies are explicit"], "verificationSteps": ["Check the slice against the workstream objective", "Confirm it is small enough for one implementation loop"], "notes": ["Do not widen this stage beyond the declared workstream."]},
        {"id": "stage-02-implement-workstream-changes", "fileName": "stage-02-implement-workstream-changes.md", "title": "Implement workstream changes", "objective": f"Implement the core changes required for: {summary}", "inputs": ["Prepared workstream slice", *scan["buildSignals"][:2]], "changeScope": ["Core implementation and integration updates"], "dependencies": ["stage-01-prepare-workstream-scope"], "acceptanceCriteria": ["Workstream behavior is implemented end to end", "Touched interfaces remain consistent"], "verificationSteps": ["Run the primary verification signal for the workstream", "Check implementation against the workstream objective"], "notes": ["Use the foundation phase outputs to constrain this work."]},
        {"id": "stage-03-verify-workstream-results", "fileName": "stage-03-verify-workstream-results.md", "title": "Verify workstream results", "objective": f"Run workstream-level verification and close findings for: {summary}", "inputs": [*scan["testSignals"], *scan["buildSignals"][:1]], "changeScope": ["Workstream verification and issue closure"], "dependencies": ["stage-02-implement-workstream-changes"], "acceptanceCriteria": ["Workstream passes targeted verification", "Blocking findings are fixed before phase close"], "verificationSteps": ["Execute targeted tests or checks", "Close detected defects before completing the phase"], "notes": ["Leave the workstream ready for final verification."]},
    ]


def materialize_phase_files(planning_root: Path, run_id: str, task_context: dict[str, Any], target_phase_ids: set[str]) -> list[dict[str, Any]]:
    updated_phases: list[dict[str, Any]] = []
    for phase in task_context["phases"]:
        phase_copy = dict(phase)
        phase_dir = planning_root / phase_copy["id"]
        phase_dir.mkdir(parents=True, exist_ok=True)
        phase_copy["path"] = relative_to(planning_root, phase_dir / "phase.md")
        phase_copy["stageOutlinePath"] = relative_to(planning_root, phase_dir / "stage-outline.md")
        stage_outline = build_stage_outline(phase_copy)
        if phase_copy["id"] in target_phase_ids:
            stage_specs = build_stage_specs(phase_copy, task_context["task"], task_context["scan"])
            phase_copy["detailStatus"] = "ready"
            phase_copy["stageFiles"] = []
            for stage in stage_specs:
                stage_path = phase_dir / stage["fileName"]
                write_text(stage_path, render_template("stage-plan.template.md", {"phase_id": phase_copy["id"], "phase_title": phase_copy["title"], "stage_id": stage["id"], "stage_title": stage["title"], "stage_objective": stage["objective"], "stage_input_lines": format_bullets(stage["inputs"]), "stage_change_scope_lines": format_bullets(stage["changeScope"]), "stage_dependency_lines": format_bullets(stage["dependencies"]), "stage_acceptance_lines": format_bullets(stage["acceptanceCriteria"]), "stage_verification_lines": format_bullets(stage["verificationSteps"]), "stage_notes_lines": format_bullets(stage["notes"])}))
                phase_copy["stageFiles"].append(relative_to(planning_root, stage_path))
        else:
            phase_copy["stageFiles"] = []
        write_text(phase_dir / "phase.md", render_template("phase.template.md", {"phase_id": phase_copy["id"], "phase_title": phase_copy["title"], "phase_type": phase_copy["type"], "detail_status": phase_copy["detailStatus"], "phase_objective": phase_copy["objective"], "dependency_lines": format_bullets(phase_copy["dependsOn"] or ["none"]), "deliverable_lines": format_bullets(phase_copy["deliverables"]), "exit_criteria_lines": format_bullets(phase_copy["exitCriteria"]), "stage_outline_path": phase_copy["stageOutlinePath"]}))
        write_text(phase_dir / "stage-outline.md", render_template("stage-outline.template.md", {"phase_id": phase_copy["id"], "phase_title": phase_copy["title"], "detail_status": phase_copy["detailStatus"], "outline_lines": format_numbered(stage_outline)}))
        updated_phases.append(phase_copy)
    return updated_phases


def current_stage_files(task_context: dict[str, Any]) -> list[str]:
    current_phase = current_executable_phase(task_context)
    if current_phase is not None:
        return list(current_phase["stageFiles"])
    return []


def flatten_ready_stage_paths(task_context: dict[str, Any]) -> list[str]:
    planning_root = Path(task_context["planningRoot"]).resolve()
    ready_stage_paths: list[str] = []
    for phase in task_context["phases"]:
        if phase.get("detailStatus") != "ready":
            continue
        for stage_file in phase.get("stageFiles", []):
            ready_stage_paths.append(str((planning_root / stage_file).resolve()))
    return ready_stage_paths


def first_pending_phase_id(phases: list[dict[str, Any]]) -> str | None:
    for phase in phases:
        if phase["detailStatus"] != "ready":
            return phase["id"]
    return None


def current_phase_id(task_context: dict[str, Any]) -> str:
    current_id = task_context.get("currentPhaseId")
    if phase_by_id(task_context["phases"], current_id) is not None:
        return current_id
    ready_phase = first_ready_phase(task_context["phases"])
    if ready_phase is not None:
        return ready_phase["id"]
    return first_pending_phase_id(task_context["phases"]) or "none"


def current_executable_phase(task_context: dict[str, Any]) -> dict[str, Any] | None:
    current_phase = phase_by_id(task_context["phases"], current_phase_id(task_context))
    if current_phase is not None and current_phase["detailStatus"] == "ready" and current_phase.get("stageFiles"):
        return current_phase
    return first_ready_phase(task_context["phases"])


def current_executable_phase_id(task_context: dict[str, Any]) -> str:
    current_phase = current_executable_phase(task_context)
    if current_phase is not None:
        return current_phase["id"]
    return current_phase_id(task_context)


def stage_plan_metadata(stage_path: str | None) -> dict[str, Any]:
    if not stage_path:
        return {"title": "none", "objective": "none", "path": "none"}
    path = Path(stage_path).resolve()
    content = read_text(path)
    title = "none"
    objective = "none"
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("Objective:"):
            objective = line.partition(":")[2].strip()
    return {"title": title, "objective": objective, "path": str(path)}


def planning_state_path(planning_root: Path) -> Path:
    return planning_root / "planning-state.aclx"


def runtime_phase_handoff_target(task_context: dict[str, Any]) -> str | None:
    runtime_root = Path(
        task_context.get("runtimeRoot")
        or runtime_root_for(task_context["projectRoot"], task_context["runId"])
    ).resolve()
    status_path = runtime_root / "status.json"
    if not status_path.exists():
        return None
    status = read_json(status_path)
    if status.get("blocker") != "missing_plan" or status.get("nextAction") != "expand_phase_plan":
        return None
    phase_id = status.get("latestVerification")
    if not phase_id or phase_id == "none":
        return None
    return str(phase_id)


def build_planning_metadata(task_context: dict[str, Any], planning_root: Path) -> dict[str, Any]:
    phase_items: list[dict[str, Any]] = []
    for phase in task_context["phases"]:
        phase_items.append(
            {
                "id": phase["id"],
                "title": phase["title"],
                "type": phase["type"],
                "detailStatus": phase["detailStatus"],
                "path": resolve_from(planning_root, phase.get("path")),
                "stageOutlinePath": resolve_from(planning_root, phase.get("stageOutlinePath")),
                "stageFiles": [
                    resolved_path
                    for resolved_path in (
                        resolve_from(planning_root, stage_path)
                        for stage_path in phase.get("stageFiles", [])
                    )
                    if resolved_path is not None
                ],
                "dependsOn": list(phase.get("dependsOn") or []),
            }
        )

    protocol_path = (planning_root / "autorun-protocol.md").resolve()
    return {
        "runId": task_context["runId"],
        "title": task_context["title"],
        "projectRoot": str(Path(task_context["projectRoot"]).resolve()),
        "planningRoot": str(planning_root.resolve()),
        "runtimeRoot": str(Path(task_context.get("runtimeRoot") or runtime_root_for(task_context["projectRoot"], task_context["runId"])).resolve()),
        "generatedAt": task_context["generatedAt"],
        "planningMode": task_context["planningMode"],
        "approvalStatus": task_context["approvalStatus"],
        "currentPhaseId": current_phase_id(task_context),
        "currentExecutablePhaseId": current_executable_phase_id(task_context),
        "firstPendingPhaseId": first_pending_phase_id(task_context["phases"]) or "none",
        "readyPhaseIds": [phase["id"] for phase in task_context["phases"] if phase["detailStatus"] == "ready"],
        "pendingPhaseIds": [
            phase["id"] for phase in task_context["phases"] if phase["detailStatus"] != "ready"
        ],
        "currentStageQueue": [
            str((planning_root / stage_path).resolve()) for stage_path in current_stage_files(task_context)
        ],
        "phases": phase_items,
        "protocolPath": str(protocol_path),
        "phaseIndexPath": str((planning_root / "phase-index.md").resolve()),
        "taskIntakePath": str((planning_root / "task-intake.md").resolve()),
        "taskContextPath": str((planning_root / "task-context.json").resolve()),
        "planningStatePath": str(planning_state_path(planning_root).resolve()),
    }


def write_phase_index(path: Path, planning_root: Path, task_context: dict[str, Any]) -> None:
    metadata = build_planning_metadata(task_context, planning_root)
    lines = [
        f"{index}. `{phase['id']}` - {phase['title']} (detailStatus: {phase['detailStatus']}, path: {phase['path']})"
        for index, phase in enumerate(task_context["phases"], start=1)
    ]
    write_text(
        path,
        render_template(
            "phase-index.template.md",
            {
                "run_id": task_context["runId"],
                "title": task_context["title"],
                "project_root": task_context["projectRoot"],
                "planning_root": planning_root,
                "runtime_root": metadata["runtimeRoot"],
                "planning_state_path": metadata["planningStatePath"],
                "approval_status": task_context["approvalStatus"],
                "current_phase_id": metadata["currentPhaseId"],
                "current_executable_phase_id": metadata["currentExecutablePhaseId"],
                "phase_lines": "\n".join(lines),
            },
        ),
    )


def write_planning_state(path: Path, planning_root: Path, task_context: dict[str, Any]) -> None:
    metadata = build_planning_metadata(task_context, planning_root)
    write_text(
        path,
        render_template(
            "planning-state.template.aclx",
            {
                "protocol_version": PLANNING_PROTOCOL_VERSION,
                "run_id": metadata["runId"],
                "title": metadata["title"],
                "generated_at": metadata["generatedAt"],
                "project_root": metadata["projectRoot"],
                "planning_root": metadata["planningRoot"],
                "runtime_root": metadata["runtimeRoot"],
                "planning_mode": metadata["planningMode"],
                "approval_status": metadata["approvalStatus"],
                "current_phase_id": metadata["currentPhaseId"],
                "current_executable_phase_id": metadata["currentExecutablePhaseId"],
                "first_pending_phase_id": metadata["firstPendingPhaseId"],
                "ready_phase_ids_json": json.dumps(metadata["readyPhaseIds"], ensure_ascii=True),
                "pending_phase_ids_json": json.dumps(metadata["pendingPhaseIds"], ensure_ascii=True),
                "phase_items_json": json.dumps(metadata["phases"], ensure_ascii=True),
                "current_stage_queue_json": json.dumps(metadata["currentStageQueue"], ensure_ascii=True),
                "protocol_path": metadata["protocolPath"],
                "phase_index_path": metadata["phaseIndexPath"],
                "task_intake_path": metadata["taskIntakePath"],
                "task_context_path": metadata["taskContextPath"],
            },
        ),
    )


def write_autorun_protocol(path: Path, planning_root: Path, task_context: dict[str, Any]) -> None:
    metadata = build_planning_metadata(task_context, planning_root)
    queue_lines = [
        f"{index}. [{relative_to(planning_root, Path(stage_file))}]({relative_to(planning_root, Path(stage_file))})"
        for index, stage_file in enumerate(metadata["currentStageQueue"], start=1)
    ]
    write_text(
        path,
        render_template(
            "autorun-protocol.template.md",
            {
                "run_id": task_context["runId"],
                "title": task_context["title"],
                "project_root": task_context["projectRoot"],
                "planning_root": planning_root,
                "planning_state_path": metadata["planningStatePath"],
                "generated_at": task_context["generatedAt"],
                "approval_status": task_context["approvalStatus"],
                "planning_mode": task_context["planningMode"],
                "current_phase_id": metadata["currentPhaseId"],
                "current_executable_phase_id": metadata["currentExecutablePhaseId"],
                "current_stage_queue_lines": "\n".join(queue_lines) or "1. none",
            },
        ),
    )


def export_planning_state(task_context: dict[str, Any], approval_status: str) -> dict[str, Any]:
    planning_root = Path(task_context["planningRoot"]).resolve()
    metadata = build_planning_metadata(task_context, planning_root)
    return {
        "runId": task_context["runId"],
        "title": task_context["title"],
        "projectRoot": task_context["projectRoot"],
        "planningRoot": str(planning_root),
        "runtimeRoot": metadata["runtimeRoot"],
        "protocolPath": metadata["protocolPath"],
        "planningStatePath": metadata["planningStatePath"],
        "taskIntakePath": metadata["taskIntakePath"],
        "taskContextPath": metadata["taskContextPath"],
        "phaseIndexPath": metadata["phaseIndexPath"],
        "planningMode": task_context["planningMode"],
        "approvalStatus": approval_status,
        "currentPhaseId": metadata["currentPhaseId"],
        "currentExecutablePhaseId": metadata["currentExecutablePhaseId"],
        "currentExecutableStages": metadata["currentStageQueue"],
        "pendingPhaseIds": metadata["pendingPhaseIds"],
        "readyPhaseIds": metadata["readyPhaseIds"],
        "firstPendingPhaseId": metadata["firstPendingPhaseId"],
    }


def resolve_phase_boundary(task_context: dict[str, Any], current_stage_path: str | None) -> dict[str, Any] | None:
    if not current_stage_path:
        return None
    current_stage = str(Path(current_stage_path).resolve())
    ready_stage_paths = flatten_ready_stage_paths(task_context)
    if current_stage in ready_stage_paths:
        current_index = ready_stage_paths.index(current_stage)
        if current_index + 1 < len(ready_stage_paths):
            next_stage_path = ready_stage_paths[current_index + 1]
            return {
                "transition": "advance_to_ready_stage",
                "queue_items": ready_stage_paths,
                "queue_cursor": current_index + 1,
                "current_stage_path": next_stage_path,
                "current_stage_id": Path(next_stage_path).stem,
            }

    current_phase_index = _find_phase_index_for_stage(task_context, current_stage)
    if current_phase_index is None:
        return None

    remaining_phases = task_context["phases"][current_phase_index + 1 :]
    if not remaining_phases:
        return {"transition": "complete_run"}

    next_phase = remaining_phases[0]
    if next_phase.get("detailStatus") == "ready" and next_phase.get("stageFiles"):
        next_stage_path = str((Path(task_context["planningRoot"]) / next_phase["stageFiles"][0]).resolve())
        if next_stage_path in ready_stage_paths:
            return {
                "transition": "advance_to_ready_stage",
                "queue_items": ready_stage_paths,
                "queue_cursor": ready_stage_paths.index(next_stage_path),
                "current_stage_path": next_stage_path,
                "current_stage_id": Path(next_stage_path).stem,
            }

    return {
        "transition": "block_for_expand",
        "phase_id": next_phase.get("id", "unknown-phase"),
        "phase_title": next_phase.get("title", "Unnamed phase"),
    }


def write_planning_bundle(*, project_root: str | Path, run_id: str, title: str, task_text: str, success_criteria: list[str], constraints: list[str], planning_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root).resolve()
    effective_planning_root = Path(planning_root).resolve() if planning_root else planning_root_for(root, run_id)
    effective_runtime_root = runtime_root_for(root, run_id)
    scan = scan_project(root)
    phases = build_phase_specs(extract_workstreams(task_text))
    phases[0]["detailStatus"] = "ready"
    task_context = {"runId": run_id, "title": title, "task": task_text, "successCriteria": success_criteria or ["Current task objective is fully implemented and verified."], "constraints": constraints or ["Do not widen scope beyond the requested task and discovered project constraints."], "projectRoot": str(root), "planningRoot": str(effective_planning_root), "runtimeRoot": str(effective_runtime_root), "generatedAt": now_iso(), "planningMode": "phase_upfront_stage_rolling", "approvalStatus": "pending", "currentPhaseId": phases[0]["id"], "scan": scan, "phases": phases}
    task_context["phases"] = materialize_phase_files(effective_planning_root, run_id, task_context, {phases[0]["id"]})
    write_text(effective_planning_root / "task-intake.md", render_template("task-intake.template.md", {"run_id": run_id, "title": title, "generated_at": task_context["generatedAt"], "project_root": root, "task_text": task_text, "success_criteria_lines": format_bullets(task_context["successCriteria"]), "constraint_lines": format_bullets(task_context["constraints"]), "stack_lines": format_bullets(scan["stackLabels"]), "doc_lines": format_bullets(shorten_paths(scan["docs"], root)), "manifest_lines": format_bullets(shorten_paths(scan["manifests"], root)), "source_dir_lines": format_bullets(shorten_paths(scan["sourceDirs"], root)), "build_signal_lines": format_bullets(scan["buildSignals"]), "test_signal_lines": format_bullets(scan["testSignals"]), "workstream_lines": format_bullets(extract_workstreams(task_text))}))
    write_json(effective_planning_root / "task-context.json", task_context)
    write_phase_index(effective_planning_root / "phase-index.md", effective_planning_root, task_context)
    write_planning_state(planning_state_path(effective_planning_root), effective_planning_root, task_context)
    write_autorun_protocol(effective_planning_root / "autorun-protocol.md", effective_planning_root, task_context)
    return export_planning_state(task_context, task_context["approvalStatus"])


def load_protocol_metadata(protocol_path: str | Path) -> dict[str, Any]:
    protocol = Path(protocol_path).resolve()
    planning_state = discover_planning_state(protocol)
    if planning_state is not None:
        return load_planning_state_acl(planning_state, protocol)

    match = JSON_BLOCK_RE.search(read_text(protocol))
    if not match:
        raise ValueError(f"Missing autorun metadata block in {protocol}")
    payload = json.loads(match.group(1))
    payload["protocolPath"] = str(protocol)
    return payload


def discover_planning_state(protocol_path: Path) -> Path | None:
    match = PLANNING_STATE_PATH_RE.search(read_text(protocol_path))
    if match:
        resolved_path = resolve_from(protocol_path.parent, match.group(1).strip())
        if resolved_path is not None:
            candidate = Path(resolved_path)
            if candidate.exists():
                return candidate.resolve()
    sibling = planning_state_path(protocol_path.parent)
    if sibling.exists():
        return sibling.resolve()
    return None


def load_planning_state_acl(
    planning_state_path_value: str | Path,
    protocol_path: str | Path | None = None,
) -> dict[str, Any]:
    aclx_path = Path(planning_state_path_value).resolve()
    entries = read_aclx(aclx_path)
    if entries.get("protocolVersion") != PLANNING_PROTOCOL_VERSION:
        raise ValueError(
            f"Unsupported planning protocolVersion {entries.get('protocolVersion')!r} in {aclx_path}"
        )
    resolved_protocol = resolve_from(aclx_path.parent, entries.get("artifacts.protocol"))
    payload = {
        "runId": entries["runId"],
        "title": entries["title"],
        "projectRoot": entries["project.root"],
        "planningRoot": entries["planning.root"],
        "runtimeRoot": entries.get("runtime.root", str(runtime_root_for(entries["project.root"], entries["runId"]))),
        "generatedAt": entries["generatedAt"],
        "planningMode": entries["planningMode"],
        "approvalStatus": entries["approval.status"],
        "currentPhaseId": entries["phase.current"],
        "currentExecutablePhaseId": entries.get("phase.executable", entries["phase.current"]),
        "firstPendingPhaseId": entries.get("phase.firstPending", "none"),
        "readyPhaseIds": parse_json_value(entries.get("phase.ready"), []),
        "pendingPhaseIds": parse_json_value(entries.get("phase.pending"), []),
        "currentStageQueue": parse_json_value(entries.get("stage.queue"), []),
        "phases": parse_json_value(entries.get("phase.items"), []),
        "protocolPath": resolved_protocol
        or str(Path(protocol_path).resolve() if protocol_path else aclx_path),
        "phaseIndexPath": resolve_from(aclx_path.parent, entries.get("artifacts.phaseIndex")),
        "taskIntakePath": resolve_from(aclx_path.parent, entries.get("artifacts.taskIntake")),
        "taskContextPath": resolve_from(aclx_path.parent, entries.get("artifacts.taskContext")),
        "planningStatePath": str(aclx_path),
    }
    return payload


def load_planning_state(planning_root: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(planning_root).resolve()
    return read_json(root / "task-context.json"), load_protocol_metadata(root / "autorun-protocol.md")


def load_task_context(planning_root: str | Path) -> dict[str, Any]:
    root = Path(planning_root).resolve()
    return read_json(root / "task-context.json")


def mark_approved(task_context: dict[str, Any]) -> dict[str, Any]:
    updated = dict(task_context)
    updated["approvalStatus"] = "approved"
    return updated


def expand_phase(*, planning_root: str | Path, phase_id: str | None = None) -> dict[str, Any]:
    root = Path(planning_root).resolve()
    task_context = read_json(root / "task-context.json")
    target_phase_id = phase_id or first_pending_phase_id(task_context["phases"])
    if target_phase_id is None:
        raise ValueError("No pending phase is available to expand.")
    target_phase = next((phase for phase in task_context["phases"] if phase["id"] == target_phase_id), None)
    if target_phase is None:
        raise ValueError(f"Unknown phase id: {target_phase_id}")
    if target_phase["detailStatus"] == "ready":
        return export_planning_state(task_context, task_context["approvalStatus"])
    task_context["phases"] = materialize_phase_files(root, task_context["runId"], task_context, {target_phase_id})
    if runtime_phase_handoff_target(task_context) == target_phase_id:
        task_context["currentPhaseId"] = target_phase_id
    write_json(root / "task-context.json", task_context)
    write_phase_index(root / "phase-index.md", root, task_context)
    write_planning_state(planning_state_path(root), root, task_context)
    write_autorun_protocol(root / "autorun-protocol.md", root, task_context)
    return export_planning_state(task_context, task_context["approvalStatus"])


def _dedupe_strings(items: list[str]) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = summarize_line(item, 160)
        if normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
    return results


def _find_phase_index_for_stage(task_context: dict[str, Any], current_stage: str) -> int | None:
    planning_root = Path(task_context["planningRoot"]).resolve()
    for index, phase in enumerate(task_context["phases"]):
        for stage_path in phase.get("stageFiles", []):
            candidate = str((planning_root / stage_path).resolve())
            if candidate == current_stage:
                return index
    return None
