import json
from dataclasses import dataclass
from typing import Iterable

from tools.base import BaseTool


@dataclass(frozen=True)
class Task:
    task_id: str
    name: str
    duration: float


class CriticalPathTool(BaseTool):
    @property
    def name(self) -> str:
        return "critical_path"

    @property
    def description(self) -> str:
        return (
            "根据任务JSON生成关键路径，参数: json_path (JSON文件路径), "
            "duration_mode (expected|normal|optimistic|pessimistic, 可选)"
        )

    def run(self, json_path: str, duration_mode: str = "expected") -> dict:
        try:
            payload = _load_json(json_path)
        except Exception as exc:
            return {"error": f"无法读取JSON文件: {exc}"}

        try:
            tasks, edges = _parse_payload(payload, duration_mode)
            result = _compute_critical_path(tasks, edges)
            result["duration_mode"] = duration_mode
            return result
        except Exception as exc:
            return {"error": f"计算关键路径失败: {exc}"}


def _load_json(path: str) -> dict:
    if not isinstance(path, str) or not path.strip():
        raise ValueError("json_path 不能为空")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_payload(payload: dict, duration_mode: str) -> tuple[dict[str, Task], list[tuple[str, str]]]:
    if not isinstance(payload, dict):
        raise ValueError("JSON 根对象必须是字典")

    tasks_raw = payload.get("tasks", [])
    deps_raw = payload.get("dependencies", [])

    if not isinstance(tasks_raw, list):
        raise ValueError("tasks 必须是数组")
    if not isinstance(deps_raw, list):
        raise ValueError("dependencies 必须是数组")

    tasks: dict[str, Task] = {}
    for item in tasks_raw:
        if not isinstance(item, dict):
            raise ValueError("tasks 元素必须是对象")
        task_id = str(item.get("id", "")).strip()
        if not task_id:
            raise ValueError("任务缺少 id")
        if task_id in tasks:
            raise ValueError(f"任务 id 重复: {task_id}")
        name = str(item.get("name", "")).strip() or task_id
        duration = _pick_duration(item, duration_mode)
        tasks[task_id] = Task(task_id=task_id, name=name, duration=duration)

    edges: list[tuple[str, str]] = []
    for dep in deps_raw:
        if not isinstance(dep, dict):
            raise ValueError("dependencies 元素必须是对象")
        frm = str(dep.get("from", "")).strip()
        to = str(dep.get("to", "")).strip()
        if not frm or not to:
            raise ValueError("dependency 需要 from 和 to")
        if frm not in tasks or to not in tasks:
            raise ValueError(f"dependency 引用未知任务: {frm} -> {to}")
        edges.append((frm, to))

    return tasks, edges


def _pick_duration(task: dict, duration_mode: str) -> float:
    mode = (duration_mode or "expected").lower()
    opt = task.get("duration_opt")
    norm = task.get("duration_norm")
    pess = task.get("duration_pess")

    if mode == "optimistic":
        value = opt
    elif mode == "normal":
        value = norm
    elif mode == "pessimistic":
        value = pess
    else:
        if opt is None or norm is None or pess is None:
            value = norm
        else:
            value = (float(opt) + 4.0 * float(norm) + float(pess)) / 6.0

    if value is None:
        raise ValueError("任务缺少持续时间字段")

    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"持续时间无效: {exc}")

    if value < 0:
        raise ValueError("持续时间不能为负数")

    return value


def _compute_critical_path(tasks: dict[str, Task], edges: Iterable[tuple[str, str]]) -> dict:
    successors: dict[str, list[str]] = {task_id: [] for task_id in tasks}
    predecessors: dict[str, list[str]] = {task_id: [] for task_id in tasks}

    for frm, to in edges:
        successors[frm].append(to)
        predecessors[to].append(frm)

    topo = _topological_sort(tasks.keys(), predecessors)

    earliest_start: dict[str, float] = {task_id: 0.0 for task_id in tasks}
    earliest_finish: dict[str, float] = {task_id: 0.0 for task_id in tasks}
    best_prev: dict[str, str | None] = {task_id: None for task_id in tasks}

    for task_id in topo:
        es = 0.0
        best = None
        for prev in predecessors[task_id]:
            candidate = earliest_finish[prev]
            if candidate > es:
                es = candidate
                best = prev
        earliest_start[task_id] = es
        earliest_finish[task_id] = es + tasks[task_id].duration
        best_prev[task_id] = best

    project_duration = max(earliest_finish.values()) if earliest_finish else 0.0
    end_tasks = [t for t, ef in earliest_finish.items() if ef == project_duration]

    latest_finish: dict[str, float] = {task_id: project_duration for task_id in tasks}
    latest_start: dict[str, float] = {task_id: 0.0 for task_id in tasks}

    for task_id in reversed(topo):
        if successors[task_id]:
            lf = min(latest_start[s] for s in successors[task_id])
        else:
            lf = project_duration
        latest_finish[task_id] = lf
        latest_start[task_id] = lf - tasks[task_id].duration

    slack: dict[str, float] = {
        task_id: round(latest_start[task_id] - earliest_start[task_id], 6)
        for task_id in tasks
    }

    critical_tasks = [task_id for task_id, value in slack.items() if abs(value) <= 1e-6]
    critical_path = _reconstruct_path(end_tasks, best_prev)

    task_table = {
        task_id: {
            "name": tasks[task_id].name,
            "duration": tasks[task_id].duration,
            "earliest_start": earliest_start[task_id],
            "earliest_finish": earliest_finish[task_id],
            "latest_start": latest_start[task_id],
            "latest_finish": latest_finish[task_id],
            "slack": slack[task_id],
        }
        for task_id in tasks
    }

    return {
        "project_duration": project_duration,
        "critical_path": critical_path,
        "critical_tasks": critical_tasks,
        "tasks": task_table,
    }


def _topological_sort(nodes: Iterable[str], predecessors: dict[str, list[str]]) -> list[str]:
    indegree = {node: len(predecessors[node]) for node in nodes}
    queue = [node for node, count in indegree.items() if count == 0]
    order: list[str] = []

    while queue:
        node = queue.pop(0)
        order.append(node)
        for nxt, preds in predecessors.items():
            if node in preds:
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)

    if len(order) != len(indegree):
        raise ValueError("依赖关系存在环")

    return order


def _reconstruct_path(end_tasks: list[str], best_prev: dict[str, str | None]) -> list[str]:
    if not end_tasks:
        return []

    end_task = end_tasks[0]
    path = [end_task]
    current = end_task
    while best_prev.get(current):
        current = best_prev[current]
        if current is None:
            break
        path.append(current)
    return list(reversed(path))
