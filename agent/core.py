import json
from agent.llm import LLMClient
from agent.tool_manager import ToolManager
from config.settings import MAX_ITERATIONS

SYSTEM_PROMPT_TEMPLATE = """你是一个有用的天气助手。你可以使用以下工具：
{tool_descriptions}

规则：如果需要查天气，必须输出JSON格式：
{{"tool": "工具名", "arguments": {{"city": "城市"}}}}
如果已拿到结果，请用自然语言回复。"""

class Agent:
    def __init__(self):
        self.llm = LLMClient()
        self.tool_manager = ToolManager()
        self.max_iter = MAX_ITERATIONS

    def _build_system_prompt(self):
        return SYSTEM_PROMPT_TEMPLATE.format(
            tool_descriptions=self.tool_manager.get_tools_prompt()
        )

    def run(self, user_message: str) -> str:
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": user_message}
        ]

        for _ in range(self.max_iter):
            reply = self.llm.chat(messages)
            messages.append({"role": "assistant", "content": reply})

            # 尝试解析工具调用
            try:
                tool_call = json.loads(reply)
                if "tool" in tool_call:
                    name = tool_call["tool"]
                    args = tool_call.get("arguments", {})
                    result = self.tool_manager.execute(name, **args)
                    tool_msg = f"工具执行结果：{json.dumps(result, ensure_ascii=False)}"
                    messages.append({"role": "user", "content": tool_msg})
                    continue
            except (json.JSONDecodeError, TypeError):
                pass  # 不是工具调用，即是最终回复

            return reply

        return "抱歉，处理超时，请稍后再试。"