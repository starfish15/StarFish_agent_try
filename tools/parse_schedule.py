import json
from dataclasses import dataclass

from agent.llm import LLMClient
from tools.base import BaseTool


_DEFAULT_DURATIONS = {
    "duration_opt": 1,
    "duration_norm": 2,
    "duration_pess": 3,
}


@dataclass(frozen=True)
class ParsedTask:
    task_id: str
    name: str
    duration_opt: float
    duration_norm: float
    duration_pess: float


class ParseScheduleTool(BaseTool):
    @property
    def name(self) -> str:
        return "parse_schedule"

    @property
    def description(self) -> str:
        return (
            "将自然语言解析为排期 JSON。"
            "参数: text (必填), output_path (可选)。"
        )

    def run(self, text: str, output_path: str | None = None) -> dict:
        if not isinstance(text, str) or not text.strip():
            return {"error": "text 为必填字段"}

        try:
            payload = _call_llm(text)
            normalized = _normalize_payload(payload)
        except Exception as exc:
            return {"error": f"解析失败: {exc}"}

        json_path = output_path or "test/generated_schedule.json"
        try:
            with open(json_path, "w", encoding="utf-8") as handle:
                json.dump(normalized, handle, ensure_ascii=False, indent=2)
        except Exception as exc:
            return {"error": f"写入 JSON 失败: {exc}"}

        return {"json_path": json_path, "payload": normalized}


def _call_llm(text: str) -> dict:
    prompt = (
        "你是项目规划助手。将输入转换为以下 JSON 结构:\n"
        "{\n"
        "  \"tasks\": [\n"
        "    {\"id\": \"T1\", \"name\": \"事件名称\", "
        "\"duration_opt\": 1, \"duration_norm\": 2, \"duration_pess\": 3}\n"
        "  ],\n"
        "  \"dependencies\": [\n"
        "    {\"from\": \"T1\", \"to\": \"T2\"}\n"
        "  ]\n"
        "}\n"
        "规则:\n"
        "- 只输出 JSON 对象，不要包含多余文字。\n"
        "- 任务 ID 按出现顺序生成 T1, T2, T3。\n"
        "- 若缺少持续时间字段，使用 duration_opt=1, duration_norm=2, duration_pess=3。\n"
        "- 依赖必须使用任务 ID。\n"
        "输入:\n"
        f"{text}"
    )

    client = LLMClient()
    messages = [{"role": "system", "content": prompt}]
    response = client.chat(messages, response_format={"type": "json_object"})
    return json.loads(response)


def _normalize_payload(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload 必须是对象")

    tasks_raw = payload.get("tasks", [])
    deps_raw = payload.get("dependencies", [])

    if not isinstance(tasks_raw, list):
        raise ValueError("tasks 必须是数组")
    if not isinstance(deps_raw, list):
        raise ValueError("dependencies 必须是数组")

    tasks: list[ParsedTask] = []
    name_to_id: dict[str, str] = {}

    for index, item in enumerate(tasks_raw):
        if not isinstance(item, dict):
            raise ValueError("task 必须是对象")
        task_id = str(item.get("id") or f"T{index + 1}").strip()
        if not task_id:
            raise ValueError("task id 为必填字段")
        name = str(item.get("name") or task_id).strip()
        duration_opt = _coerce_number(item.get("duration_opt"), _DEFAULT_DURATIONS["duration_opt"])
        duration_norm = _coerce_number(item.get("duration_norm"), _DEFAULT_DURATIONS["duration_norm"])
        duration_pess = _coerce_number(item.get("duration_pess"), _DEFAULT_DURATIONS["duration_pess"])

        tasks.append(
            ParsedTask(
                task_id=task_id,
                name=name,
                duration_opt=duration_opt,
                duration_norm=duration_norm,
                duration_pess=duration_pess,
            )
        )
        if name:
            name_to_id[name] = task_id

    task_ids = {task.task_id for task in tasks}
    dependencies: list[dict[str, str]] = []
    for dep in deps_raw:
        if not isinstance(dep, dict):
            raise ValueError("dependency 必须是对象")
        frm = str(dep.get("from") or "").strip()
        to = str(dep.get("to") or "").strip()
        if not frm or not to:
            raise ValueError("dependency 需要 from 和 to")
        frm = name_to_id.get(frm, frm)
        to = name_to_id.get(to, to)
        if frm not in task_ids or to not in task_ids:
            raise ValueError(f"未知依赖: {frm} -> {to}")
        dependencies.append({"from": frm, "to": to})

    return {
        "tasks": [
            {
                "id": task.task_id,
                "name": task.name,
                "duration_opt": task.duration_opt,
                "duration_norm": task.duration_norm,
                "duration_pess": task.duration_pess,
            }
            for task in tasks
        ],
        "dependencies": dependencies,
    }


def _coerce_number(value, fallback: float) -> float:
    if value is None:
        return float(fallback)
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float(fallback)
    if number < 0:
        return float(fallback)
    return number
