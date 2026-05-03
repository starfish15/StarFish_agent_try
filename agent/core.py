import json
from agent.llm import LLMClient
from agent.tool_manager import ToolManager
from config.settings import ENABLED_SKILLS, ENABLED_TOOLS, MAX_ITERATIONS, SKILL_MODEL, SKILL_TEMPERATURE
from skills.skill_manager import SkillManager

class Agent:
    def __init__(self):
        self.llm = LLMClient()
        self.tool_manager = ToolManager(enabled_tools=ENABLED_TOOLS)
        self.skill_manager = SkillManager(
            enabled_skills=ENABLED_SKILLS,
            temperature=SKILL_TEMPERATURE,
            model=SKILL_MODEL,
        )
        self.max_iter = MAX_ITERATIONS

    def _build_system_prompt(self):
        return self.skill_manager.build_system_prompt(self.tool_manager.get_tools_prompt())

    def run(self, user_message: str) -> str:
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": user_message}
        ]

        llm_options = self.skill_manager.merged_llm_options()

        for _ in range(self.max_iter):
            reply = self.llm.chat(messages, **llm_options)
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