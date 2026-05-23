from __future__ import annotations

from typing import Iterable

from skills.base import BaseSkill
from skills.file_skill_loader import load_skills_from_dir
from skills.json_tool_calling import JsonToolCallingSkill
from skills.llm_tuning import LlmTuningSkill
from config.settings import LOAD_FILE_SKILLS, SKILL_DEFINITIONS_DIR


class SkillManager:
    def __init__(
        self,
        enabled_skills: Iterable[str] | None = None,
        *,
        temperature: float | None = None,
        model: str | None = None,
    ):
        self.skills: dict[str, BaseSkill] = {}
        self.always_on_skills: list[BaseSkill] = []
        self._register_builtin_skills(temperature=temperature, model=model)

        if LOAD_FILE_SKILLS:
            for loaded in load_skills_from_dir(SKILL_DEFINITIONS_DIR):
                self.register(loaded.skill)

        if enabled_skills is not None:
            enabled = {s.strip() for s in enabled_skills if s and s.strip()}
            self.skills = {name: skill for name, skill in self.skills.items() if name in enabled}

    def _register_builtin_skills(self, *, temperature: float | None, model: str | None):
        # Ordering matters: prefix first, tool list in the middle, suffix last.

        self.register(LlmTuningSkill(temperature=temperature, model=model))
        self.register(JsonToolCallingSkill())

    def register(self, skill: BaseSkill) -> None:
        if skill.always_on:
            self.always_on_skills.append(skill)
        else:
            self.skills[skill.name] = skill

    def get_skill_descriptions(self) -> str:
        """Get a formatted string of all skill names and descriptions."""
        return "\n".join(
            f"- {skill.name}: {skill.description}"
            for skill in self.skills.values()
            if skill.selectable
        )

    def get_skills_by_names(self, names: list[str]) -> list[BaseSkill]:
        """Return a list of skills that match the given names."""
        return [self.skills[name] for name in names if name in self.skills]

    def get_all_skills(self) -> list[BaseSkill]:
        return list(self.skills.values()) + list(self.always_on_skills)

    def get_skills_by_group(self, group: str) -> list[BaseSkill]:
        if not group:
            return []
        return [skill for skill in self.get_all_skills() if skill.exclusive_group == group]

    def get_always_on_skills(self) -> list[BaseSkill]:
        """Return the list of skills that are always active."""
        return self.always_on_skills

    def dedupe_skills(self, skills: list[BaseSkill]) -> list[BaseSkill]:
        seen: set[str] = set()
        result: list[BaseSkill] = []
        for skill in skills:
            if skill.name in seen:
                continue
            seen.add(skill.name)
            result.append(skill)
        return result

    def apply_exclusive_groups(
        self,
        skills: list[BaseSkill],
        preferred_by_group: dict[str, str] | None = None,
    ) -> list[BaseSkill]:
        if not skills:
            return []

        preferred_by_group = preferred_by_group or {}
        chosen_by_group: dict[str, str] = {}

        grouped: dict[str, list[BaseSkill]] = {}
        for skill in skills:
            group = skill.exclusive_group
            if group:
                grouped.setdefault(group, []).append(skill)

        for group, items in grouped.items():
            preferred_name = preferred_by_group.get(group)
            if preferred_name:
                match = next((s for s in items if s.name == preferred_name), None)
                if match:
                    chosen_by_group[group] = match.name
                    continue
            if items:
                chosen_by_group[group] = items[0].name

        result: list[BaseSkill] = []
        for skill in skills:
            group = skill.exclusive_group
            if not group:
                result.append(skill)
                continue
            if chosen_by_group.get(group) == skill.name:
                result.append(skill)

        return result

    def build_system_prompt(self, tool_descriptions: str, active_skills: list[BaseSkill]) -> str:
        prefixes = [s.system_prompt_prefix().strip() for s in active_skills if s.system_prompt_prefix().strip()]
        suffixes = [s.system_prompt_suffix().strip() for s in active_skills if s.system_prompt_suffix().strip()]
        wants_tools = any(getattr(s, "uses_tools", False) for s in active_skills)

        parts: list[str] = []
        parts.extend(prefixes)
        if wants_tools and tool_descriptions.strip():
            parts.append("你可以使用以下工具：\n" + tool_descriptions.strip())
        parts.extend(suffixes)
        return "\n\n".join(parts).strip()

    def merged_llm_options(self, active_skills: list[BaseSkill]) -> dict:
        merged: dict = {}
        for skill in active_skills:
            merged.update(skill.llm_options() or {})
        return merged
