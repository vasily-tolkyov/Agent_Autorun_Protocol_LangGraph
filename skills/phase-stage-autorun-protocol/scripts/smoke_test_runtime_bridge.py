from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from run_phase_stage_autorun import __file__ as AUTORUN_WRAPPER_PATH


SCRIPT_DIR = Path(__file__).resolve().parent
SKILLS_ROOT = SCRIPT_DIR.parents[1]
AUTOPLAN_WRAPPER = SKILLS_ROOT / "phase-stage-autoplan-entry" / "scripts" / "run_phase_stage_autoplan.py"


def run_wrapper(entrypoint: Path, args: list[str]) -> dict:
    output = subprocess.check_output([sys.executable, str(entrypoint), *args], text=True)
    return json.loads(output)


def run_autorun(args: list[str]) -> dict:
    output = subprocess.check_output(
        [sys.executable, str(Path(AUTORUN_WRAPPER_PATH).resolve()), *args],
        text=True,
    )
    return json.loads(output)


def assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="phase-stage-autorun-v2-") as temp_dir:
        root = Path(temp_dir)
        project_root = root / "project"
        (project_root / "src").mkdir(parents=True, exist_ok=True)
        (project_root / "README.md").write_text("# Demo Project\n", encoding="utf-8", newline="\n")
        (project_root / "package.json").write_text(
            '{"name":"demo","scripts":{"test":"vitest","build":"vite build"}}\n',
            encoding="utf-8",
            newline="\n",
        )

        intake = run_wrapper(
            AUTOPLAN_WRAPPER,
            [
                "intake",
                "--project-root",
                str(project_root),
                "--run-id",
                "demo-run",
                "--title",
                "Demo Autorun",
                "--task",
                "Implement a staged demo workflow and verify it.",
            ],
        )
        planning_root = Path(intake["planningRoot"])
        approval = run_wrapper(AUTOPLAN_WRAPPER, ["approve", "--planning-root", str(planning_root)])
        runtime_root = Path(approval["planning"]["runtimeRoot"])

        executor_result_path = root / "executor-result.json"
        executor_result_path.write_text(
            json.dumps(
                {
                    "kind": "executor_result",
                    "summary": "Stage build completed",
                    "changed_files": ["README.md"],
                    "verification_evidence": ["build-ok", "tests-ok"],
                    "verdict_or_status": "SUCCESS",
                    "blocker_or_none": "none",
                    "recommended_next_action": "start_audit",
                    "state_delta": {"latest_verification": "tests-ok"},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

        continued = run_autorun(
            [
                "continue",
                "--planning-root",
                str(planning_root),
                "--executor-result-json",
                str(executor_result_path),
            ]
        )
        assert_equal(continued["graphId"], "phase_stage_autorun", "continue returns autorun graph id")
        assert_equal(continued["status"], "interrupted", "continue lands on verification interrupt")
        assert_equal(continued["state"]["stage_state"], "build_verified", "executor result advances outer stage state")
        assert_equal(continued["state"]["verification_phase"], "dispatch_critic", "inner loop begins with critic dispatch")
        assert_equal(continued["interrupts"][0]["value"]["kind"], "critic_request", "continue requests critic review")
        assert_equal((runtime_root / "runtime-view.aclx").exists(), True, "runtime export remains current")

        status = run_autorun(["status", "--planning-root", str(planning_root)])
        assert_equal(status["handles"]["phase_stage_autorun"]["graph_id"], "phase_stage_autorun", "status reports autorun handle")

        exported = run_autorun(["export", "--planning-root", str(planning_root)])
        assert_equal(Path(exported["exports"]["runtime_view"]).exists(), True, "export returns runtime view path")

    print("phase-stage-autorun-protocol LangGraph smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
