from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        Path(temp_name).replace(path)
    finally:
        temp_path = Path(temp_name)
        if temp_path.exists():
            temp_path.unlink()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(read_text(path))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def render_template(name: str, mapping: dict[str, Any]) -> str:
    content = read_text(TEMPLATE_DIR / name)
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


def format_bullets(items: list[str]) -> str:
    cleaned = [item for item in items if item]
    return "\n".join(f"- {item}" for item in cleaned) if cleaned else "- none"


def format_numbered(items: list[str]) -> str:
    cleaned = [item for item in items if item]
    return (
        "\n".join(f"{index}. {item}" for index, item in enumerate(cleaned, start=1))
        if cleaned
        else "1. none"
    )


def summarize_line(text: str, max_chars: int = 100) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def shorten_paths(paths: list[str], root: Path) -> list[str]:
    shortened: list[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        try:
            shortened.append(relative_to(root, path))
        except ValueError:
            shortened.append(str(path))
    return shortened


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
