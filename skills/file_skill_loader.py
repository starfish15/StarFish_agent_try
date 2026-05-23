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
    for path in sorted(base.rglob("*.skill.md")):
        if not path.is_file():
            continue
        loaded.append(LoadedSkill(skill=_load_one(path), path=path))
    return loaded


def _load_one(path: Path) -> FileSkill:
    text = path.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(text)

    # Preferred authoring experience: chaptered Markdown (Claude Code-like).
    # Frontmatter remains supported for backward compatibility.
    if meta:
        name = str(meta.get("name") or _default_name(path)).strip()
        if not name:
            raise ValueError(f"Skill 文件缺少 name: {path}")

        display_name = str(meta.get("display_name") or meta.get("displayName") or "").strip()
        description = str(meta.get("description") or "").strip()

        uses_tools = bool(meta.get("uses_tools", False))
        always_on = bool(meta.get("always_on", False))
        selectable = bool(meta.get("selectable", True))
        exclusive_group = str(
            meta.get("exclusive_group")
            or meta.get("exclusiveGroup")
            or meta.get("group")
            or ""
        ).strip()

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
    else:
        parsed = _parse_chaptered_markdown(body)
        name = (parsed.get("name") or _default_name(path)).strip()
        if not name:
            raise ValueError(f"Skill 文件缺少 name: {path}")

        display_name = (parsed.get("display_name") or "").strip()
        description = (parsed.get("description") or "").strip()
        uses_tools = bool(parsed.get("uses_tools", False))
        always_on = bool(parsed.get("always_on", False))
        selectable = bool(parsed.get("selectable", True))
        exclusive_group = str(parsed.get("exclusive_group") or "").strip()
        prompt_prefix = (parsed.get("prompt_prefix") or "").strip()
        prompt_suffix = (parsed.get("prompt_suffix") or "").strip()

        llm = parsed.get("llm") or {}
        if not isinstance(llm, dict):
            raise ValueError(f"LLM 章节内容必须能解析为 dict: {path}")

    return FileSkill(
        name=name,
        display_name=display_name or name,
        description=description,
        prompt_prefix=prompt_prefix,
        prompt_suffix=prompt_suffix,
        llm=llm,
        source=path.name,
        uses_tools=uses_tools,
        always_on=always_on,
        selectable=selectable,
        exclusive_group=exclusive_group,
    )


def _parse_chaptered_markdown(body: str) -> dict[str, Any]:
    """Parse a chaptered Markdown skill file.

    Authoring style (example):

    ## Name
    my_skill

    ## LLM
    temperature: 0.2
    model: deepseek-v4-flash

    ## Rules
    ...

    ## Prompt Suffix
    ...

    Behavior:
    - Name/Description/LLM are treated as metadata (not injected into prompt)
    - Prompt Suffix section becomes suffix
    - All other sections are injected into prompt_prefix, keeping headings
    - If no sections exist, entire body becomes prompt_prefix
    """
    sections = _split_markdown_sections(body)
    if not sections:
        return {"prompt_prefix": body.strip()}

    def norm(h: str) -> str:
        return " ".join(h.strip().lower().split())

    name = ""
    description = ""
    display_name = ""
    llm: dict[str, Any] = {}
    uses_tools = False
    always_on = False
    selectable = True
    exclusive_group = ""
    suffix_chunks: list[str] = []
    prefix_chunks: list[str] = []

    for heading, content in sections:
        h = norm(heading)
        c = (content or "").strip()

        if h in {"name", "skill name", "skill"}:
            if c:
                name = c.splitlines()[0].strip()
            continue

        if h in {"description", "desc"}:
            description = c
            continue

        if h in {"display name", "display_name", "title"}:
            if c:
                display_name = c.splitlines()[0].strip()
            continue

        if h in {"llm", "model", "tuning", "parameters"}:
            if c:
                parsed = yaml.safe_load(c) or {}
                if not isinstance(parsed, dict):
                    raise ValueError("LLM 章节必须是 YAML mapping/dict")
                llm = parsed
            continue

        if h in {"tools", "tool", "uses tools", "use tools"}:
            if c:
                parsed = yaml.safe_load(c) or {}
                if isinstance(parsed, dict):
                    uses_tools = bool(parsed.get("enabled", parsed.get("uses_tools", False)))
                else:
                    uses_tools = bool(str(c).strip().lower() in {"1", "true", "yes", "on"})
            else:
                uses_tools = True
            continue

        if h in {"selectable", "llm selectable", "auto select"}:
            if c:
                parsed = yaml.safe_load(c) or {}
                if isinstance(parsed, dict):
                    selectable = bool(parsed.get("enabled", parsed.get("selectable", True)))
                else:
                    selectable = bool(str(c).strip().lower() in {"1", "true", "yes", "on"})
            else:
                selectable = True
            continue

        if h in {"always on", "always_on", "auto"}:
            if c:
                parsed = yaml.safe_load(c) or {}
                if isinstance(parsed, dict):
                    always_on = bool(parsed.get("enabled", parsed.get("always_on", False)))
                else:
                    always_on = bool(str(c).strip().lower() in {"1", "true", "yes", "on"})
            else:
                always_on = True
            continue

        if h in {"exclusive group", "exclusive_group", "group"}:
            if c:
                exclusive_group = c.splitlines()[0].strip()
            continue

        if h in {"prompt suffix", "suffix", "post", "after tools"}:
            if c:
                suffix_chunks.append(_render_section(heading, c, keep_heading=False))
            continue

        # Everything else is part of the prompt, keep the chaptered experience.
        if c:
            prefix_chunks.append(_render_section(heading, c, keep_heading=True))

    if not prefix_chunks and body.strip():
        prefix = body.strip()
    else:
        prefix = "\n\n".join(prefix_chunks).strip()

    suffix = "\n\n".join(suffix_chunks).strip()

    return {
        "name": name,
        "description": description,
        "display_name": display_name,
        "llm": llm,
        "uses_tools": uses_tools,
        "always_on": always_on,
        "selectable": selectable,
        "exclusive_group": exclusive_group,
        "prompt_prefix": prefix,
        "prompt_suffix": suffix,
    }


def _split_markdown_sections(text: str) -> list[tuple[str, str]]:
    """Split Markdown by H2 headings (## ...).

    Returns list of (heading, content). If no H2 headings found, returns [].
    """
    lines = text.splitlines()
    indices: list[int] = []
    headings: list[str] = []
    for i, line in enumerate(lines):
        if line.startswith("## "):
            indices.append(i)
            headings.append(line[3:].strip())

    if not indices:
        return []

    sections: list[tuple[str, str]] = []
    for idx, start in enumerate(indices):
        end = indices[idx + 1] if idx + 1 < len(indices) else len(lines)
        heading = headings[idx]
        content = "\n".join(lines[start + 1 : end]).strip("\n")
        sections.append((heading, content))

    return sections


def _render_section(heading: str, content: str, *, keep_heading: bool) -> str:
    if keep_heading:
        return f"## {heading}\n{content}".strip()
    return content.strip()


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
