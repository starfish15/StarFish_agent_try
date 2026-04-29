from tools.weather import WeatherTool

class ToolManager:
    def __init__(self):
        self.tools = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        weather = WeatherTool()
        self.tools[weather.name] = weather

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