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
    @abstractmethod
    def description(self) -> str:
        """Short description for humans."""

    def system_prompt_prefix(self) -> str:
        """Content placed before the tool list in the system prompt."""
        return ""

    def system_prompt_suffix(self) -> str:
        """Content placed after the tool list in the system prompt."""
        return ""

    def llm_options(self) -> dict[str, Any]:
        """LLM parameters override, e.g. {"temperature": 0.2, "model": "..."}."""
        return {}
