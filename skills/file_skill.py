from __future__ import annotations

from typing import Any

from skills.base import BaseSkill


class FileSkill(BaseSkill):
    def __init__(
        self,
        *,
        name: str,
        description: str = "",
        prompt_prefix: str = "",
        prompt_suffix: str = "",
        llm: dict[str, Any] | None = None,
        source: str | None = None,
    ):
        self._name = name
        self._description = description
        self._prompt_prefix = prompt_prefix
        self._prompt_suffix = prompt_suffix
        self._llm = llm or {}
        self._source = source

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        if self._description:
            return self._description
        return f"File skill ({self._source or 'unknown'})"

    def system_prompt_prefix(self) -> str:
        return self._prompt_prefix

    def system_prompt_suffix(self) -> str:
        return self._prompt_suffix

    def llm_options(self) -> dict[str, Any]:
        llm = self._llm or {}
        opts: dict[str, Any] = {}
        if "temperature" in llm and llm["temperature"] is not None:
            opts["temperature"] = float(llm["temperature"])
        if "model" in llm and llm["model"]:
            opts["model"] = str(llm["model"])
        return opts
