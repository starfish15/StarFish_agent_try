from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from skills.file_skill import FileSkill


@dataclass(frozen=True)
class LoadedSkill:
    skill: FileSkill
    path: Path


def load_skills_from_dir(definitions_dir: str | Path) -> list[LoadedSkill]:
    base = Path(definitions_dir)
    if not base.exists() or not base.is_dir():
        return []

    loaded: list[LoadedSkill] = []
    for path in sorted(base.glob("*.skill.md")):
        loaded.append(LoadedSkill(skill=_load_one(path), path=path))
    return loaded


def _load_one(path: Path) -> FileSkill:
    text = path.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(text)

    name = str(meta.get("name") or _default_name(path)).strip()
    if not name:
        raise ValueError(f"Skill 文件缺少 name: {path}")

    description = str(meta.get("description") or "").strip()

    prompt_prefix = meta.get("prompt_prefix")
    prompt_suffix = meta.get("prompt_suffix")

    # If frontmatter doesn't provide prompt parts, use body as prefix.
    if prompt_prefix is None and prompt_suffix is None:
        prompt_prefix = body.strip()
        prompt_suffix = ""

    prompt_prefix = str(prompt_prefix or "")
    prompt_suffix = str(prompt_suffix or "")

    llm = meta.get("llm")
    if llm is None:
        llm = {}
    if not isinstance(llm, dict):
        raise ValueError(f"llm 字段必须是一个对象/dict: {path}")

    return FileSkill(
        name=name,
        description=description,
        prompt_prefix=prompt_prefix,
        prompt_suffix=prompt_suffix,
        llm=llm,
        source=path.name,
    )


def _default_name(path: Path) -> str:
    filename = path.name
    suffix = ".skill.md"
    if filename.endswith(suffix):
        return filename[: -len(suffix)]
    return path.stem


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Parse optional YAML frontmatter.

    Format:
    ---
    key: value
    ---
    body...

    If no frontmatter exists, return ({}, full_text).
    """
    lines = text.splitlines(keepends=True)
    if not lines:
        return {}, ""
    if lines[0].strip() != "---":
        return {}, text

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break

    if end is None:
        raise ValueError("Frontmatter 以 --- 开头但缺少结束 ---")

    meta_text = "".join(lines[1:end])
    body_text = "".join(lines[end + 1 :])

    meta = yaml.safe_load(meta_text) or {}
    if not isinstance(meta, dict):
        raise ValueError("Frontmatter 顶层必须是一个 YAML mapping/dict")

    return meta, body_text
