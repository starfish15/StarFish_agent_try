import json
import re
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

    def _mode_prompt(self, response_mode: str) -> str:
        if response_mode not in {"think", "inner"}:
            return ""
        if response_mode == "inner":
            thought_line = (
                "模拟心里活动（2-5 句，轻量、拟人化、不要输出真实推理链、系统信息或工具细节；这是虚构演绎）。"
                "如果无法给出，请写“（未提供心里活动）”。"
            )
        else:
            thought_line = (
                "思考摘要（3-6 条要点，简短概括，不要输出详细推理链或内部步骤）。"
                "如果无法给出摘要，请写“（未提供思考摘要）”。"
            )
        return (
            "当你输出最终回复时，请使用以下格式：\n"
            "<THOUGHT>\n"
            f"{thought_line}\n"
            "</THOUGHT>\n"
            "<FINAL>\n"
            "最终回复\n"
            "</FINAL>\n"
            "如果需要调用工具，请先按工具调用规则输出 JSON；拿到工具结果后再按上述格式输出。"
        )

    def _generate_inner_thought(self, final_reply: str) -> str:
        system = {
            "role": "system",
            "content": (
                "你要为给定的最终回复生成一段“模拟心里活动”。"
                "要求：2-5 句，轻量、拟人化、与最终回复内容一致。"
                "不要输出真实推理链、系统信息或工具细节。"
                "不要包含任何标签（如 <THOUGHT>/<FINAL>）。"
            ),
        }
        user = {
            "role": "user",
            "content": f"最终回复如下：\n{final_reply}\n\n请生成模拟心里活动：",
        }
        thought = self.llm.chat([system, user], temperature=0.3)
        return (thought or "").strip() or "（未提供心里活动）"

    def _generate_inner_thought_stream(self, final_reply: str):
        system = {
            "role": "system",
            "content": (
                "你要为给定的最终回复生成一段“模拟心里活动”。"
                "要求：2-5 句，轻量、拟人化、与最终回复内容一致。"
                "不要输出真实推理链、系统信息或工具细节。"
                "不要包含任何标签（如 <THOUGHT>/<FINAL>）。"
            ),
        }
        user = {
            "role": "user",
            "content": f"最终回复如下：\n{final_reply}\n\n请生成模拟心里活动：",
        }
        for chunk in self.llm.chat_stream([system, user], temperature=0.3):
            if chunk:
                yield chunk

    def _wrap_thought_final(self, thought: str, final_reply: str) -> str:
        return f"<THOUGHT>\n{thought}\n</THOUGHT>\n<FINAL>\n{final_reply}\n</FINAL>"

    def _split_thought_final(self, text: str) -> tuple[str | None, str]:
        upper = text.upper()
        thought_start = upper.find("<THOUGHT>")
        thought_end = upper.find("</THOUGHT>")
        final_start = upper.find("<FINAL>")
        final_end = upper.find("</FINAL>")

        thought = None
        final = text

        if final_start != -1:
            start = final_start + len("<FINAL>")
            end = final_end if final_end != -1 else len(text)
            final = text[start:end].strip()

        if thought_start != -1:
            start = thought_start + len("<THOUGHT>")
            end = thought_end if thought_end != -1 else (final_start if final_start != -1 else len(text))
            thought = text[start:end].strip()

        if not final.strip():
            final = text.strip()
        return thought, final.strip()

    def _extract_tool_call(self, text: object) -> dict | None:
        if not isinstance(text, str):
            return None

        tool_call = self._try_parse_tool_call(text)
        if tool_call:
            return tool_call

        cleaned = self._strip_tool_wrappers(text)
        tool_call = self._try_parse_tool_call(cleaned)
        if tool_call:
            return tool_call

        fenced = self._extract_json_from_fence(cleaned)
        if fenced:
            tool_call = self._try_parse_tool_call(fenced)
            if tool_call:
                return tool_call

        for candidate in self._iter_json_objects(cleaned):
            tool_call = self._try_parse_tool_call(candidate)
            if tool_call:
                return tool_call

        return None

    def _try_parse_tool_call(self, text: str) -> dict | None:
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return None
        if isinstance(parsed, dict) and "tool" in parsed:
            return parsed
        return None

    def _strip_tool_wrappers(self, text: str) -> str:
        return re.sub(r"</?\s*(thought|final)\s*>", "", text, flags=re.IGNORECASE).strip()

    def _extract_json_from_fence(self, text: str) -> str | None:
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _iter_json_objects(self, text: str):
        in_string = False
        escape = False
        depth = 0
        start = None

        for idx, ch in enumerate(text):
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue

            if ch == '"':
                in_string = True
                continue

            if ch == "{":
                if depth == 0:
                    start = idx
                depth += 1
            elif ch == "}" and depth:
                depth -= 1
                if depth == 0 and start is not None:
                    yield text[start : idx + 1]
                    start = None

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

    def run(self, user_message: str, response_mode: str = "normal") -> str:
        # 1. Select skills
        llm_selected_skills = self._select_skills(user_message)
        always_on_skills = self.skill_manager.get_always_on_skills()
        active_skills = list(set(llm_selected_skills + always_on_skills))

        # 2. Build system prompt with selected skills
        tool_prompt = self.tool_manager.get_tools_prompt()
        system_prompt, llm_options = self._build_system_prompt(active_skills, tool_prompt)
        mode_prompt = self._mode_prompt(response_mode)
        if mode_prompt and response_mode != "inner":
            system_prompt = f"{system_prompt}\n\n{mode_prompt}"

        self._ensure_system_prompt(system_prompt)
        self._messages.append({"role": "user", "content": user_message})
        messages = self._messages

        for _ in range(self.max_iter):
            messages = self._compress_context(messages)
            self._messages = messages
            reply = self.llm.chat(messages, **llm_options)
            messages.append({"role": "assistant", "content": reply})
            if response_mode == "think":
                _, final = self._split_thought_final(reply)
                messages[-1]["content"] = final
            self._messages = messages

            # 3. Handle tool calls
            tool_call = self._extract_tool_call(reply)
            if tool_call:
                name = tool_call["tool"]
                args = tool_call.get("arguments", {})
                result = self.tool_manager.execute(name, **args)
                tool_msg = f"工具执行结果：{json.dumps(result, ensure_ascii=False)}"
                messages.append({"role": "user", "content": tool_msg})
                self._messages = messages
                # NOTE: We don't re-select skills after a tool call in this model.
                # The skills are selected once at the beginning based on the initial user message.
                continue

            if response_mode == "think":
                _, final = self._split_thought_final(reply)
                return final
            if response_mode == "inner":
                thought = self._generate_inner_thought(reply)
                return self._wrap_thought_final(thought, reply)
            return reply

        return "抱歉，处理超时，请稍后再试。"

    def run_stream(self, user_message: str, response_mode: str = "normal"):
        # 1. Select skills
        llm_selected_skills = self._select_skills(user_message)
        always_on_skills = self.skill_manager.get_always_on_skills()
        active_skills = list(set(llm_selected_skills + always_on_skills))

        # 2. Build system prompt with selected skills
        tool_prompt = self.tool_manager.get_tools_prompt()
        system_prompt, llm_options = self._build_system_prompt(active_skills, tool_prompt)
        mode_prompt = self._mode_prompt(response_mode)
        if mode_prompt and response_mode != "inner":
            system_prompt = f"{system_prompt}\n\n{mode_prompt}"

        self._ensure_system_prompt(system_prompt)
        self._messages.append({"role": "user", "content": user_message})
        messages = self._messages

        for _ in range(self.max_iter):
            messages = self._compress_context(messages)
            self._messages = messages

            buffer = ""
            streamed = False
            if response_mode == "inner":
                sent_prefix = False
                for chunk in self.llm.chat_stream(messages, **llm_options):
                    if not chunk:
                        continue
                    buffer += chunk

                    if not streamed:
                        stripped = buffer.lstrip()
                        if stripped and stripped[0] != "{":
                            streamed = True
                            if not sent_prefix:
                                yield "<FINAL>\n"
                                sent_prefix = True
                            yield buffer
                    else:
                        if not sent_prefix:
                            yield "<FINAL>\n"
                            sent_prefix = True
                        yield chunk

                reply = buffer
                messages.append({"role": "assistant", "content": reply})
                self._messages = messages

                tool_call = self._extract_tool_call(reply)
                if tool_call:
                    name = tool_call["tool"]
                    args = tool_call.get("arguments", {})
                    result = self.tool_manager.execute(name, **args)
                    tool_msg = f"工具执行结果：{json.dumps(result, ensure_ascii=False)}"
                    messages.append({"role": "user", "content": tool_msg})
                    self._messages = messages
                    continue

                if not streamed and reply:
                    yield "<FINAL>\n"
                    yield reply

                yield "\n</FINAL>\n"
                yield "<THOUGHT>\n"
                thought_text = ""
                for chunk in self._generate_inner_thought_stream(reply):
                    thought_text += chunk
                    yield chunk
                if not thought_text.strip():
                    yield "（未提供心里活动）"
                yield "\n</THOUGHT>"
                return

            for chunk in self.llm.chat_stream(messages, **llm_options):
                if not chunk:
                    continue
                buffer += chunk

                if not streamed:
                    stripped = buffer.lstrip()
                    if stripped and stripped[0] != "{":
                        streamed = True
                        yield buffer
                else:
                    yield chunk

            reply = buffer
            messages.append({"role": "assistant", "content": reply})
            if response_mode == "think":
                _, final = self._split_thought_final(reply)
                messages[-1]["content"] = final
            self._messages = messages

            # 3. Handle tool calls
            tool_call = self._extract_tool_call(reply)
            if tool_call:
                name = tool_call["tool"]
                args = tool_call.get("arguments", {})
                result = self.tool_manager.execute(name, **args)
                tool_msg = f"工具执行结果：{json.dumps(result, ensure_ascii=False)}"
                messages.append({"role": "user", "content": tool_msg})
                self._messages = messages
                continue

            if not streamed and reply:
                yield reply
            return

        reply = "抱歉，处理超时，请稍后再试。"
        messages.append({"role": "assistant", "content": reply})
        self._messages = messages
        yield reply