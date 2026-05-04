# StarFish_agent_try
一个用于学习 Agent 与技能（skill）体系的最小化项目。重点是：
- tools/ 负责“对外动作”
- skills/ 负责“模型调优与提示词”
- Agent 负责将两者拼装成可运行的对话流程

---

## 项目结构
```
main.py
agent/
    core.py         # Agent 入口与对话主流程
    llm.py          # LLM 客户端封装
    tool_manager.py # Tool 管理与执行
config/
    settings.py     # 环境变量与运行配置
skills/
    base.py
    file_skill.py
    file_skill_loader.py
    json_tool_calling.py
    llm_tuning.py
    skill_manager.py
    definitions/    # 可直接编辑的 .skill.md 文件
tools/
    base.py
    calculator.py
    weather.py
```

---

## 快速开始
1) 安装依赖：
```bash
uv sync
```

2) 配置 API Key（.env 或环境变量）：
```bash
DEEPSEEK_API_KEY=your_key
```

3) 启动：
```bash
uv run main.py
```

---

## Agent 工作流程（简版）
1) 收到用户输入后，LLM 先根据技能描述选择需要启用的 skills
2) SkillManager 将选中的 skills 拼成 system_prompt
3) 如果启用了可用工具的 skill，提示词会注入工具列表
4) LLM 可能输出工具调用 JSON，ToolManager 执行后回传结果
5) LLM 继续回答用户

---

## Tools：对外动作
Tool 用于执行外部动作（HTTP、查询、计算、读写等）。模型通过输出 JSON 触发执行，结果会以 `工具执行结果：{...}` 回传给模型。

### 新增 Tool
1) 在 `tools/` 新建类，继承 `BaseTool`：
- `name`：工具唯一名字
- `description`：给模型看的说明（写清参数）
- `run(**kwargs) -> dict`：执行逻辑，返回可 JSON 序列化的字典

2) 注册工具：
- 内置工具：在 `agent/tool_manager.py` 的 `_register_builtin_tools()` 中实例化并加入 `self.tools`
- 动态注册：运行时调用 `ToolManager.register(tool)`

### 工具调用协议
```json
{"tool": "get_weather", "arguments": {"city": "shanghai"}}
```

### 示例：calculate
内置示例工具位于 `tools/calculator.py`，工具名 `calculate`，参数 `expression`。

---

## Skills：模型调优
Skill 只负责“调优模型”（system prompt 片段 + LLM 参数），不做任何外部副作用。

### 内置 Skills
- `json_tool_calling`：允许工具调用并给出 JSON 规则
- `llm_tuning`：通过环境变量覆盖 `temperature` / `model`

### File Skill（推荐）
默认会从 `skills/definitions/` 加载 `.skill.md` 文件（可通过环境变量关闭）。
当前项目内的技能采用 Frontmatter + 纯正文的格式（可参考现有的 `.skill.md` 文件）。

#### 创建一个新的 Skill
在 `skills/definitions/` 新建 `xxx.skill.md`，格式如下：
```markdown
---
name: your_skill_name
description: "对这个 Skill 的简短描述"
# uses_tools: true   # 可选：需要工具列表时开启
# always_on: true    # 可选：常驻启用，跳过 LLM 选择
---
这里写注入到 system_prompt 的内容。
```

说明：
- `uses_tools` 为 `true` 时会注入工具列表与调用规则
- `always_on` 为 `true` 时会跳过技能选择阶段

### Skill 选择机制
LLM 会根据 `name` + `description` 返回技能列表，Agent 只激活这些技能（`always_on: true` 会跳过选择阶段）。

### Tool 调用由 Skill 决定
只有启用了 `uses_tools` 的 skill 才会注入工具列表与调用规则。

---

## 环境变量
基础配置：
- `DEEPSEEK_API_KEY`：LLM API Key（必填）
- `LLM_BASE_URL`：API Base URL，默认 `https://api.deepseek.com`
- `LLM_MODEL`：默认模型名，默认 `deepseek-chat`
- `MAX_ITERATIONS`：一次对话最多工具循环次数，默认 5

技能与工具控制：
- `ENABLED_TOOLS`：逗号分隔，仅启用指定工具
- `ENABLED_SKILLS`：逗号分隔，仅启用指定技能
- `LOAD_FILE_SKILLS`：是否加载 `skills/definitions/`（默认开启）
- `SKILL_DEFINITIONS_DIR`：技能文件目录（默认 `skills/definitions`）

模型调优（配合 `llm_tuning`）：
- `SKILL_TEMPERATURE`：覆盖温度
- `SKILL_MODEL`：覆盖模型名（会覆盖 `LLM_MODEL`）

示例：只保留天气工具 + 只允许指定技能
```bash
ENABLED_TOOLS=get_weather
ENABLED_SKILLS=llm_tuning,json_tool_calling,cat_persona
SKILL_TEMPERATURE=0.0
```
