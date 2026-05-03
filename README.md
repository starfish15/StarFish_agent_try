# StarFish_agent_try
尝试搭建一个简易的agent项目，主要目的是学习agent与agent_skill相关的内容并尝试进行一次项目架构

---

## 使用说明
该项目运用uv进行管理，在克隆仓库后请在项目根目录使用`uv sync`下载相关依赖。

如果你想与该智能体对话，请按照
`StarFish_agent_try\config\.env.example`
的格式在`config`文件夹下创建对应的`.env`配置文件

创建好配置文件后，你可以在项目根目录使用`uv run main.py`来运行智能体

---

## 如何添加 Tool（可被模型调用的工具）
Tool 的职责是“对外动作”（HTTP 请求、查询、计算、读写等）。模型通过输出 JSON 触发 tool 执行（协议由 skill 约束），执行结果会以“工具执行结果：{...}”喂回模型继续回答。

新增一个 Tool 的最小步骤：

1) 在 `tools/` 新建一个工具类，继承 `BaseTool`，实现：
- `name`: 工具唯一名字（字符串），模型会在 JSON 里用它
- `description`: 给模型看的简短说明（包含参数名更好）
- `run(**kwargs) -> dict`: 执行逻辑，返回可 JSON 序列化的字典

2) 在 `agent/tool_manager.py` 里注册：
- 内置工具：在 `_register_builtin_tools()` 中实例化并放进 `self.tools`
- 或者在运行时调用 `ToolManager.register(tool)` 动态追加

3) 运行并测试对话：
当模型需要调用工具时，会“只输出 JSON”，形如：

```json
{"tool": "get_weather", "arguments": {"city": "shanghai"}}
```

项目会执行对应工具，并把结果作为下一轮输入喂回 LLM：
`工具执行结果：{...}`

### 示例：内置的 calculate 工具
本仓库已经提供了一个示例工具：`tools/calculator.py`（工具名 `calculate`），参数为 `expression`。

你可以这样问：
- 你：帮我算 (1 + 2) * 3
- Agent（可能会先输出工具调用 JSON）：
	`{"tool": "calculate", "arguments": {"expression": "(1 + 2) * 3"}}`
- Agent（拿到工具结果后）：返回计算结果

---

## 分开管理 tools 与 skills（推荐）
为了让 “工具（tools）” 和 “模型调优（skills）” 分开管理：

- `tools/`：对外动作（HTTP 请求、查询、计算、读写等），会被模型通过 JSON 触发执行
- `skills/`：只做模型调优（system prompt 片段、输出风格约束、LLM 参数如 temperature/model），不做任何外部副作用

### 如何添加 Skill（主要用于调优模型）
Skill 的职责是“调优模型”，包括：
- system prompt 片段（人设、语气、格式约束、策略等）
- LLM 参数（temperature / model 等）

新增一个 Skill 的最小步骤：
1) 在 `skills/` 下新建一个 skill 类，继承 `BaseSkill`，实现：
- `name` / `description`
- `system_prompt_prefix()` / `system_prompt_suffix()`：返回要拼进 system prompt 的文本（可选）
- `llm_options()`：返回要覆盖的 LLM 参数（可选）

2) 在 `skills/skill_manager.py` 的 `_register_builtin_skills()` 里注册该 skill

3) 用 `ENABLED_SKILLS=...` 控制启用哪些 skills

### 用“类似 Claude Code 的 Markdown 格式”写 skills
如果你更喜欢用“提示词文件”的方式维护 skill，而不是写 Python 类，可以启用文件式 skill：

1) 在 `.env` 里开启：

```bash
LOAD_FILE_SKILLS=1
SKILL_DEFINITIONS_DIR=skills/definitions
```

2) 在 `skills/definitions/` 下创建 `*.skill.md`，支持 YAML frontmatter：

```md
---
name: my_skill
description: 一句话描述
llm:
	temperature: 0.2
	# model: deepseek-v4-flash
prompt_prefix: |
	这里是要拼进 system prompt 前半段的内容
prompt_suffix: |
	这里是要拼进 system prompt 后半段的内容
---
```

仓库里有一个可直接参考的示例文件：`skills/definitions/example_tuning.skill.md`。

你可以分别用环境变量控制启用项：

- `ENABLED_TOOLS`：逗号分隔，只暴露指定工具给 agent（不设置则默认全部内置工具启用）
- `ENABLED_SKILLS`：逗号分隔，只启用指定 skill（不设置则默认全部内置 skill 启用）

以及用 skill 来调优模型参数（可选）：

- `SKILL_TEMPERATURE`：覆盖温度
- `SKILL_MODEL`：覆盖模型名（会覆盖 `LLM_MODEL`）

示例：只保留天气工具 + 关闭猫娘人设

```bash
ENABLED_TOOLS=get_weather
ENABLED_SKILLS=llm_tuning,json_tool_calling
SKILL_TEMPERATURE=0.0
```

（后续会做UI界面的吧）