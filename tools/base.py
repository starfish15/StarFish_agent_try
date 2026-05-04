from abc import ABC, abstractmethod

class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name used in tool calls."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description shown to the LLM."""

    @abstractmethod
    def run(self, **kwargs) -> dict:
        """Execute the tool.

        Return a JSON-serializable dict.
        """