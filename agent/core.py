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

    def _select_skills(self, user_message: str) -> list[BaseSkill]:
        """Let the LLM choose which skills to activate."""
        skill_descriptions = self.skill_manager.get_skill_descriptions()
        prompt = (
            "根据用户的输入，判断需要启用哪些技能。你的回答必须是一个JSON数组，其中只包含技能的名称。
"
            "可用的技能如下：
"
            f"{skill_descriptions}

"
            "如果不需要启用任何技能，请返回一个空数组[]。
"
            "用户的输入是: "
            f'"{user_message}"'
        )

        messages = [{"role": "system", "content": prompt}]
        try:
            response = self.llm.chat(messages, response_format={"type": "json_object"})
            selected_skill_names = json.loads(response)
            if isinstance(selected_skill_names, list):
                return self.skill_manager.get_skills_by_names(selected_skill_names)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"技能选择失败: {e}")  # For debugging
            return []
        return []

    def _build_system_prompt(self, active_skills: list, tool_prompt: str) -> tuple[str, dict]:
        prompt = self.skill_manager.build_system_prompt(tool_prompt, active_skills)
        llm_options = self.skill_manager.merged_llm_options(active_skills)
        return prompt, llm_options

    def run(self, user_message: str) -> str:
        # 1. Select skills
        active_skills = self._select_skills(user_message)

        # 2. Build system prompt with selected skills
        tool_prompt = self.tool_manager.get_tools_prompt()
        system_prompt, llm_options = self._build_system_prompt(active_skills, tool_prompt)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        for _ in range(self.max_iter):
            reply = self.llm.chat(messages, **llm_options)
            messages.append({"role": "assistant", "content": reply})

            # 3. Handle tool calls
            try:
                tool_call = json.loads(reply)
                if "tool" in tool_call:
                    name = tool_call["tool"]
                    args = tool_call.get("arguments", {})
                    result = self.tool_manager.execute(name, **args)
                    tool_msg = f"工具执行结果：{json.dumps(result, ensure_ascii=False)}"
                    messages.append({"role": "user", "content": tool_msg})
                    # NOTE: We don't re-select skills after a tool call in this model.
                    # The skills are selected once at the beginning based on the initial user message.
                    continue
            except (json.JSONDecodeError, TypeError):
                pass  # Not a tool call, it's the final reply

            return reply

        return "抱歉，处理超时，请稍后再试。"