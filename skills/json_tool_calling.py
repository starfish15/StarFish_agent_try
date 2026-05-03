from skills.base import BaseSkill


class JsonToolCallingSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "json_tool_calling"

    @property
    def description(self) -> str:
        return "要求需要用工具时只输出一段 JSON（tool/arguments 协议）"

    def system_prompt_suffix(self) -> str:
        return (
            "工具调用规则（非常重要）：\n"
            "- 只有在你确实需要调用工具时，才输出且只输出一段 JSON（不要带额外文字）。\n"
            "- JSON 格式固定为：\n"
            '    {"tool": "工具名", "arguments": {"参数名": "参数值"}}\n'
            "- 工具执行结果会以“工具执行结果：{...}”的形式返回给你；拿到结果后，用自然语言回答用户。"
        )
