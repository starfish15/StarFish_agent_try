from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    """A skill tunes the model behavior, not the outside world.

    In this project:
    - tools/ : do actions (HTTP calls, DB, file I/O, etc.)
    - skills/: tune the LLM (prompting, style, parameters)

    Skills should be side-effect free.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique skill name used for enabling/disabling."""

    @property
    def description(self) -> str:
        """Short description for humans."""
        return ""

    @property
    def always_on(self) -> bool:
        """If True, this skill is always active and not selected by LLM."""
        return False

    @property
    def uses_tools(self) -> bool:
        """If True, include tool list and tool rules for this skill."""
        return False

    @property
    def selectable(self) -> bool:
        """If False, exclude from LLM auto-selection."""
        return True

    @property
    def exclusive_group(self) -> str:
        """Non-empty group name means only one skill in the group may be active."""
        return ""

    @property
    def display_name(self) -> str:
        """Short, user-facing name for UI display."""
        return self.name

    def system_prompt_prefix(self) -> str:
        """Content placed before the tool list in the system prompt."""
        return ""

    def system_prompt_suffix(self) -> str:
        """Content placed after the tool list in the system prompt."""
        return ""

    def llm_options(self) -> dict[str, Any]:
        """LLM parameters override, e.g. {"temperature": 0.2, "model": "..."}."""
        return {}
