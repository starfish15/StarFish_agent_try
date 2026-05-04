from __future__ import annotations

from skills.base import BaseSkill


class LlmTuningSkill(BaseSkill):
    """Centralized model tuning.

    This skill is intentionally small: it only outputs llm_options().
    """

    def __init__(self, *, temperature: float | None = None, model: str | None = None):
        self._temperature = temperature
        self._model = model

    @property
    def name(self) -> str:
        return "llm_tuning"

    @property
    def description(self) -> str:
        return "通过配置统一调优 LLM 参数（temperature/model）"

    def llm_options(self):
        opts: dict[str, object] = {}
        if self._temperature is not None:
            opts["temperature"] = float(self._temperature)
        if self._model:
            opts["model"] = self._model
        return opts
