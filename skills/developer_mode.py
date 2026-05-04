from skills.base import BaseSkill


class DeveloperModeSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "developer_mode"

    @property
    def description(self) -> str:
        return "启用开发者模式，你将扮演一名资深开发者，详细解释你的思考过程和代码实现。"

    def system_prompt_prefix(self) -> str:
        return (
            "你现在是一名资深开发者。在回答问题或执行任务时，"
            "请详细说明你的思考过程、方案选择和关键实现步骤。"
        )
