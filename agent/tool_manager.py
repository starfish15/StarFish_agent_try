from tools.weather import WeatherTool
from tools.calculator import CalculatorTool
from tools.critical_path import CriticalPathTool
from tools.parse_schedule import ParseScheduleTool

class ToolManager:
    def __init__(self, enabled_tools: list[str] | None = None):
        self.tools = {}
        self._register_builtin_tools()

        if enabled_tools is not None:
            enabled = {t.strip() for t in enabled_tools if t and t.strip()}
            self.tools = {name: tool for name, tool in self.tools.items() if name in enabled}

    def _register_builtin_tools(self):
        weather = WeatherTool()
        self.tools[weather.name] = weather

        calculator = CalculatorTool()
        self.tools[calculator.name] = calculator

        critical_path = CriticalPathTool()
        self.tools[critical_path.name] = critical_path

        parse_schedule = ParseScheduleTool()
        self.tools[parse_schedule.name] = parse_schedule

    def register(self, tool):
        """支持动态追加新工具"""
        self.tools[tool.name] = tool

    def get_tool(self, name):
        return self.tools.get(name)

    def get_tools_prompt(self):
        """生成注入给LLM的工具说明"""
        descriptions = []
        for tool in self.tools.values():
            descriptions.append(f"- {tool.name}: {tool.description}")
        return "\n".join(descriptions)

    def execute(self, name, **kwargs):
        tool = self.get_tool(name)
        if tool:
            return tool.run(**kwargs)
        return {"error": f"未知工具: {name}"}