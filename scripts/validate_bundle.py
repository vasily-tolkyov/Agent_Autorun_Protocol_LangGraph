from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILLS_ROOT = ROOT / "skills"
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

REQUIRED_SKILLS = [
    "phase-stage-autoplan-entry",
    "phase-stage-autorun-protocol",
    "generator-critic-verification-loop",
    "phase-stage-langgraph-runtime",
]

REQUIRED_ROOT_FILES = [
    ROOT / "README.md",
    ROOT / "README.zh-CN.md",
    ROOT / "INSTALL.md",
    ROOT / "INSTALL.zh-CN.md",
    ROOT / "CHANGELOG.md",
    ROOT / "LICENSE",
    ROOT / ".gitignore",
    ROOT / "scripts" / "install.py",
    ROOT / "scripts" / "install.ps1",
    ROOT / ".github" / "workflows" / "validate.yml",
]


def validate_file_exists(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Missing required bundle file: {path}")


def validate_skill(skill_root: Path) -> None:
    if not skill_root.exists():
        raise SystemExit(f"Missing skill directory: {skill_root}")

    skill_md = skill_root / "SKILL.md"
    if skill_md.exists():
        content = skill_md.read_text(encoding="utf-8")
        match = FRONTMATTER_RE.match(content)
        if not match:
            raise SystemExit(f"Missing YAML frontmatter in {skill_md}")
        frontmatter = match.group(1)
        if "name:" not in frontmatter or "description:" not in frontmatter:
            raise SystemExit(f"Missing required frontmatter keys in {skill_md}")
        agents_yaml = skill_root / "agents" / "openai.yaml"
        if not agents_yaml.exists():
            raise SystemExit(f"Missing agents/openai.yaml: {agents_yaml}")
        return

    pyproject = skill_root / "pyproject.toml"
    langgraph_json = skill_root / "langgraph.json"
    client_script = skill_root / "scripts" / "phase_stage_client.py"
    if not pyproject.exists() or not langgraph_json.exists() or not client_script.exists():
        raise SystemExit(f"Runtime skill is incomplete: {skill_root}")


def validate_no_local_runtime_artifacts() -> None:
    banned = [
        ROOT / "skills" / "phase-stage-langgraph-runtime" / ".venv",
        ROOT / "skills" / "phase-stage-langgraph-runtime" / ".langgraph_api",
        ROOT / "skills" / "phase-stage-langgraph-runtime" / "var",
        ROOT / "skills" / "phase-stage-langgraph-runtime" / ".env",
    ]
    for path in banned:
        if path.exists():
            raise SystemExit(f"Bundle should not include local runtime artifact: {path}")


def main() -> int:
    for path in REQUIRED_ROOT_FILES:
        validate_file_exists(path)

    for skill_name in REQUIRED_SKILLS:
        validate_skill(SKILLS_ROOT / skill_name)

    validate_no_local_runtime_artifacts()
    print(f"bundle validation passed for {len(REQUIRED_SKILLS)} skills")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
