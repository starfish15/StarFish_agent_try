import json
from agent.llm import LLMClient
from agent.tool_manager import ToolManager
from config.settings import (
    CONTEXT_KEEP_LAST,
    DEBUG_CONTEXT_COMPRESSION,
    ENABLED_SKILLS,
    ENABLED_TOOLS,
    MAX_CONTEXT_CHARS,
    MAX_ITERATIONS,
    SKILL_MODEL,
    SKILL_TEMPERATURE,
    SUMMARY_MAX_CHARS,
)
from skills.base import BaseSkill
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
        self._summary = ""
        self._messages: list[dict] = []

    def _ensure_system_prompt(self, system_prompt: str) -> None:
        if self._messages and self._messages[0].get("role") == "system":
            self._messages[0]["content"] = system_prompt
            return
        self._messages = [{"role": "system", "content": system_prompt}] + self._messages

    def _select_skills(self, user_message: str) -> list[BaseSkill]:
        """Let the LLM choose which skills to activate."""
        skill_descriptions = self.skill_manager.get_skill_descriptions()
        prompt = (
            """根据用户的输入，判断需要启用哪些技能。你的回答必须是一个JSON数组，其中只包含技能的名称。
可用的技能如下：
"""
            f"{skill_descriptions}"
            """如果不需要启用任何技能，请返回一个空数组[]。
用户的输入是: """
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

    def _messages_char_count(self, messages: list[dict]) -> int:
        return sum(len(m.get("content", "")) for m in messages)

    def _summarize_messages(self, messages: list[dict]) -> str:
        if not messages:
            return self._summary

        # Keep the summary concise and stable across updates.
        system = {
            "role": "system",
            "content": (
                "你是一个对话摘要器。请把对话压缩成简洁的要点摘要，"
                "只保留关键信息、用户意图、约束和已确定结论。"
                "不要包含闲聊或重复内容。只输出摘要文本。"
            ),
        }
        history_text = "\n".join(
            f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages
        )
        user = {
            "role": "user",
            "content": (
                "已有摘要：\n"
                f"{self._summary}\n\n"
                "待压缩对话：\n"
                f"{history_text}\n\n"
                f"请输出更新后的摘要（不超过 {SUMMARY_MAX_CHARS} 字符）。"
            ),
        }
        summary = self.llm.chat([system, user], temperature=0.0)
        return summary[:SUMMARY_MAX_CHARS].strip()

    def _compress_context(self, messages: list[dict]) -> list[dict]:
        if not messages or self._messages_char_count(messages) <= MAX_CONTEXT_CHARS:
            return messages

        system_msg = messages[0]
        rest = messages[1:]
        if len(rest) <= CONTEXT_KEEP_LAST:
            return messages

        to_summarize = rest[:-CONTEXT_KEEP_LAST]
        keep = rest[-CONTEXT_KEEP_LAST:]
        self._summary = self._summarize_messages(to_summarize)

        if DEBUG_CONTEXT_COMPRESSION:
            print(
                "Context compressed: "
                f"summary_chars={len(self._summary)}, "
                f"kept_messages={len(keep)}, "
                f"total_messages={len(messages)}"
            )

        summary_msg = {
            "role": "system",
            "content": "对话摘要（供参考，非原文）：\n" + self._summary,
        }
        return [system_msg, summary_msg] + keep

    def run(self, user_message: str) -> str:
        # 1. Select skills
        llm_selected_skills = self._select_skills(user_message)
        always_on_skills = self.skill_manager.get_always_on_skills()
        active_skills = list(set(llm_selected_skills + always_on_skills))

        # 2. Build system prompt with selected skills
        tool_prompt = self.tool_manager.get_tools_prompt()
        system_prompt, llm_options = self._build_system_prompt(active_skills, tool_prompt)

        self._ensure_system_prompt(system_prompt)
        self._messages.append({"role": "user", "content": user_message})
        messages = self._messages

        for _ in range(self.max_iter):
            messages = self._compress_context(messages)
            self._messages = messages
            reply = self.llm.chat(messages, **llm_options)
            messages.append({"role": "assistant", "content": reply})
            self._messages = messages

            # 3. Handle tool calls
            try:
                tool_call = json.loads(reply)
                if "tool" in tool_call:
                    name = tool_call["tool"]
                    args = tool_call.get("arguments", {})
                    result = self.tool_manager.execute(name, **args)
                    tool_msg = f"工具执行结果：{json.dumps(result, ensure_ascii=False)}"
                    messages.append({"role": "user", "content": tool_msg})
                    self._messages = messages
                    # NOTE: We don't re-select skills after a tool call in this model.
                    # The skills are selected once at the beginning based on the initial user message.
                    continue
            except (json.JSONDecodeError, TypeError):
                pass  # Not a tool call, it's the final reply

            return reply

        return "抱歉，处理超时，请稍后再试。"