from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLED_SKILLS_ROOT = REPO_ROOT / "skills"
DEFAULT_CODEX_HOME = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).resolve()
REQUIRED_SKILLS = [
    "phase-stage-autoplan-entry",
    "phase-stage-autorun-protocol",
    "generator-critic-verification-loop",
    "phase-stage-langgraph-runtime",
]
RUNTIME_DEPENDENCIES = [
    "langgraph-cli[inmem]",
    "langgraph",
    "langgraph-sdk",
    "langchain-core",
    "langgraph-checkpoint-sqlite",
    "python-dotenv",
]


def scripts_dir(root: Path) -> Path:
    return root / ".venv" / ("Scripts" if os.name == "nt" else "bin")


def venv_python(root: Path) -> Path:
    return scripts_dir(root) / ("python.exe" if os.name == "nt" else "python")


def langgraph_executable(root: Path) -> Path:
    return scripts_dir(root) / ("langgraph.exe" if os.name == "nt" else "langgraph")


def command_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def run(command: list[str], *, cwd: Path) -> None:
    print(f"[install] {' '.join(command)}", flush=True)
    subprocess.run(command, cwd=str(cwd), env=command_env(), check=True)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install the LangGraph edition of Agent Autorun Protocol into CODEX_HOME/skills."
    )
    parser.add_argument("--codex-home", default=str(DEFAULT_CODEX_HOME))
    parser.add_argument("--force", action="store_true", help="Overwrite existing installed skill directories.")
    parser.add_argument(
        "--skip-runtime-setup",
        action="store_true",
        help="Copy the skills only and skip the LangGraph virtual environment/bootstrap work.",
    )
    parser.add_argument(
        "--start-server",
        action="store_true",
        help="Start the installed LangGraph dev server after setup completes.",
    )
    return parser.parse_args(argv)


def remove_tree(path: Path, *, allowed_parent: Path) -> None:
    resolved = path.resolve()
    parent = allowed_parent.resolve()
    if resolved == parent or parent not in resolved.parents:
        raise RuntimeError(f"Refusing to remove path outside install root: {resolved}")
    shutil.rmtree(resolved)


def copy_skill(src: Path, dest: Path, *, force: bool, install_root: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Missing bundled skill directory: {src}")
    if dest.exists():
        if not force:
            raise FileExistsError(
                f"Target skill already exists: {dest}\nRe-run with --force to overwrite the installed copy."
            )
        remove_tree(dest, allowed_parent=install_root)
    shutil.copytree(src, dest)


def ensure_env_file(runtime_root: Path) -> None:
    env_path = runtime_root / ".env"
    example_path = runtime_root / ".env.example"
    if env_path.exists() or not example_path.exists():
        return
    env_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")


def setup_runtime(runtime_root: Path) -> None:
    python_path = venv_python(runtime_root)
    langgraph_path = langgraph_executable(runtime_root)
    if not python_path.exists():
        run([sys.executable, "-m", "venv", str(runtime_root / ".venv")], cwd=runtime_root)
    run([str(python_path), "-m", "pip", "install", "-U", "pip", "setuptools", "wheel"], cwd=runtime_root)
    run([str(python_path), "-m", "pip", "install", "-U", *RUNTIME_DEPENDENCIES], cwd=runtime_root)
    run([str(python_path), "-m", "pip", "install", "-e", "."], cwd=runtime_root)
    ensure_env_file(runtime_root)
    run([str(langgraph_path), "validate", "--config", str(runtime_root / "langgraph.json")], cwd=runtime_root)


def maybe_start_server(runtime_root: Path) -> None:
    if not (runtime_root / "scripts" / "phase_stage_client.py").exists():
        raise FileNotFoundError(f"Missing runtime client script in {runtime_root}")
    run([str(venv_python(runtime_root)), str(runtime_root / "scripts" / "phase_stage_client.py"), "server", "start"], cwd=runtime_root)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    codex_home = Path(args.codex_home).expanduser().resolve()
    install_root = codex_home / "skills"
    install_root.mkdir(parents=True, exist_ok=True)

    print(f"[install] Repo root: {REPO_ROOT}", flush=True)
    print(f"[install] CODEX_HOME: {codex_home}", flush=True)
    print(f"[install] Target skills root: {install_root}", flush=True)

    for skill_name in REQUIRED_SKILLS:
        copy_skill(
            BUNDLED_SKILLS_ROOT / skill_name,
            install_root / skill_name,
            force=args.force,
            install_root=install_root,
        )

    runtime_root = install_root / "phase-stage-langgraph-runtime"
    if not args.skip_runtime_setup:
        setup_runtime(runtime_root)
        if args.start_server:
            maybe_start_server(runtime_root)

    print("[install] Installation complete.", flush=True)
    print(f"[install] Installed skills: {', '.join(REQUIRED_SKILLS)}", flush=True)
    print(f"[install] Runtime root: {runtime_root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
