from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from run_phase_stage_autoplan import __file__ as AUTOPLAN_WRAPPER_PATH


def run_autoplan(args: list[str]) -> dict:
    output = subprocess.check_output(
        [sys.executable, str(Path(AUTOPLAN_WRAPPER_PATH).resolve()), *args],
        text=True,
    )
    return json.loads(output)


def assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="phase-stage-autoplan-v2-") as temp_dir:
        root = Path(temp_dir)
        project_root = root / "project"
        (project_root / "src").mkdir(parents=True, exist_ok=True)
        (project_root / "README.md").write_text("# Demo Project\n", encoding="utf-8", newline="\n")
        (project_root / "package.json").write_text(
            '{"name":"demo","scripts":{"test":"vitest","build":"vite build"}}\n',
            encoding="utf-8",
            newline="\n",
        )

        intake = run_autoplan(
            [
                "intake",
                "--project-root",
                str(project_root),
                "--run-id",
                "demo-run",
                "--title",
                "Demo Intake",
                "--task",
                "Implement a staged demo workflow and verify it.",
            ]
        )
        planning_root = Path(intake["planningRoot"])
        assert_equal(planning_root.exists(), True, "planning root exists")
        assert_equal(intake["approvalStatus"], "pending", "intake leaves plan pending")
        assert_equal((planning_root / "planning-state.aclx").exists(), True, "planning ACL-X export exists")
        assert_equal((planning_root / "autorun-protocol.md").exists(), True, "autorun protocol export exists")
        assert_equal(len(intake["currentExecutableStages"]) >= 1, True, "current executable stages exist")
        assert_equal(len(intake["pendingPhaseIds"]) >= 1, True, "future phases stay pending")

        status = run_autoplan(["status", "--planning-root", str(planning_root)])
        assert_equal(status["handles"]["phase_stage_planning"]["graph_id"], "phase_stage_planning", "status reports planning handle")

        approval = run_autoplan(["approve", "--planning-root", str(planning_root)])
        runtime_root = Path(approval["planning"]["runtimeRoot"])
        assert_equal(approval["planning"]["approvalStatus"], "approved", "approve marks plan approved")
        assert_equal(approval["autorun"]["status"], "interrupted", "approve boots autorun into executor interrupt")
        assert_equal((runtime_root / "runtime-view.aclx").exists(), True, "runtime ACL-X compatibility export exists")
        assert_equal((runtime_root / "resume-handle.json").exists(), True, "resume handle exists")

        next_phase_id = intake["pendingPhaseIds"][0]
        expanded = run_autoplan(
            [
                "expand-phase",
                "--planning-root",
                str(planning_root),
                "--phase-id",
                next_phase_id,
            ]
        )
        assert_equal(next_phase_id in expanded["readyPhaseIds"], True, "expand-phase moves target phase to ready")
        expanded_phase_dir = planning_root / next_phase_id
        assert_equal(expanded_phase_dir.exists(), True, "expanded phase directory exists")
        assert_equal(any(expanded_phase_dir.glob("stage-*.md")), True, "expanded phase writes stage plans")

    print("phase-stage-autoplan-entry LangGraph smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
