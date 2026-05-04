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
Skill 的职责是“调优模型”，它通过向 `system_prompt` 注入指令来改变模型的行为，例如调整语气、设定角色、规定输出格式等。

当前项目架构下，**推荐通过创建 Markdown 文件来添加新的 Skill**。

**新增一个 Skill 的步骤：**

1.  在 `skills/definitions/` 目录下创建一个新的 `.skill.md` 文件。
2.  在文件中使用以下格式编写 Skill：

    ```markdown
    ---
    name: your_skill_name
    description: "对这个 Skill 的简短描述，这段描述会展示给 LLM，让它判断是否需要激活此 Skill。"
    ---
    这里写下当 Skill 被激活时，需要注入到 system_prompt 的具体指令。
    你可以详细地描述模型的角色、语气、思考过程、输出格式等。
    ```

3.  **（可选）在 `.env` 文件中启用 `LOAD_FILE_SKILLS`** (默认已在 `config/settings.py` 中开启):
    ```bash
    LOAD_FILE_SKILLS=1
    SKILL_DEFINITIONS_DIR=skills/definitions
    ```

完成以上步骤后，Agent 将在启动时自动加载你的新 Skill。

### Skill 的工作原理：由 LLM 动态选择

本 Agent 的一个核心特性是**由 LLM 自主决定在对话中激活哪些 Skill**。工作流程如下：

1.  **技能选择阶段**: 当收到用户输入后，Agent 会首先将所有已加载 Skill 的 `name` 和 `description` 整合起来，向 LLM 发起一次“元调用”（meta-call）。这个调用的目的是询问 LLM：“根据用户的这句话，你认为应该激活以下哪些技能？”
2.  **执行阶段**: LLM 会返回一个它认为需要激活的 Skill 名称列表（例如 `["cat_persona", "developer_mode"]`）。Agent 随后只加载这些被选中的 Skill，并使用它们的指令来构建最终的 `system_prompt`，然后与用户进行正式的对话。

这个设计使得 Agent 更加灵活和智能。你只需要专注于编写功能明确、描述清晰的 Skill，而无需编写复杂的激活逻辑。

### 环境变量
你可以通过环境变量来控制 Agent 的行为：

- `ENABLED_TOOLS`：逗号分隔，只暴露指定工具给 agent（不设置则默认全部内置工具启用）。
- `ENABLED_SKILLS`：逗号分隔，只加载指定的 skill（不设置则默认全部 skill 都可被 LLM 选择）。

以及用内置的 `llm_tuning` skill 来调优模型参数（可选）：

- `SKILL_TEMPERATURE`：覆盖温度
- `SKILL_MODEL`：覆盖模型名（会覆盖 `LLM_MODEL`）

示例：只保留天气工具 + 只让 `developer_mode` 可选

```bash
ENABLED_TOOLS=get_weather
ENABLED_SKILLS=developer_mode,llm_tuning,json_tool_calling
SKILL_TEMPERATURE=0.0
```

（后续会做UI界面的吧）
