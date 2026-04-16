from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from run_generator_critic_loop import __file__ as GENERATOR_WRAPPER_PATH


def run_loop(args: list[str]) -> dict:
    output = subprocess.check_output(
        [sys.executable, str(Path(GENERATOR_WRAPPER_PATH).resolve()), *args],
        text=True,
    )
    return json.loads(output)


def assert_equal(actual, expected, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected {expected!r}, got {actual!r}")


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="generator-critic-loop-v2-") as temp_dir:
        root = Path(temp_dir)
        project_root = root / "project"
        project_root.mkdir(parents=True, exist_ok=True)

        input_path = root / "loop-input.json"
        input_path.write_text(
            json.dumps(
                {
                    "graph_id": "generator_critic_loop",
                    "run_id": "loop-run",
                    "project_root": str(project_root),
                    "planning_root": str(project_root / "plans" / "phase-stage-langgraph" / "loop-run"),
                    "runtime_root": str(project_root / ".codex" / "phase-stage-langgraph" / "loop-run"),
                    "phase_id": "phase-01",
                    "stage_id": "stage-01",
                    "current_execution_plan_id": "stage-01",
                    "release_candidate_id": "candidate-01",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

        started = run_loop(
            [
                "continue",
                "--project-root",
                str(project_root),
                "--run-id",
                "loop-run",
                "--input-json",
                str(input_path),
            ]
        )
        assert_equal(started["graphId"], "generator_critic_loop", "continue returns generator graph id")
        assert_equal(started["status"], "interrupted", "continue lands on first interrupt")
        assert_equal(started["interrupts"][0]["value"]["kind"], "critic_request", "first interrupt requests critic")

        result_path = root / "critic-pass.json"
        result_path.write_text(
            json.dumps(
                {
                    "kind": "critic_result",
                    "summary": "Looks good",
                    "changed_files": [],
                    "verification_evidence": ["pass-1"],
                    "verdict_or_status": "PASS",
                    "blocker_or_none": "none",
                    "recommended_next_action": "continue_critic",
                    "state_delta": {},
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )

        resumed = run_loop(
            [
                "resume",
                "--project-root",
                str(project_root),
                "--run-id",
                "loop-run",
                "--executor-result-json",
                str(result_path),
            ]
        )
        assert_equal(resumed["status"], "interrupted", "resume keeps loop running before terminal accept")
        assert_equal(resumed["state"]["clean_pass_streak"], 1, "pass increments clean pass streak")
        assert_equal(resumed["interrupts"][0]["value"]["kind"], "critic_request", "loop re-dispatches critic until streak goal")

        exported = run_loop(
            [
                "export",
                "--project-root",
                str(project_root),
                "--run-id",
                "loop-run",
            ]
        )
        assert_equal(Path(exported["exports"]["runtime_view"]).exists(), True, "export returns runtime view path")

    print("generator-critic-verification-loop LangGraph smoke test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
