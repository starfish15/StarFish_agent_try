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
        always_on: bool = False,
        uses_tools: bool = False,
    ):
        self._name = name
        self._description = description
        self._prompt_prefix = prompt_prefix
        self._prompt_suffix = prompt_suffix
        self._llm = llm or {}
        self._source = source
        self._always_on = always_on
        self._uses_tools = uses_tools

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def always_on(self) -> bool:
        return self._always_on

    @property
    def uses_tools(self) -> bool:
        return self._uses_tools

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
