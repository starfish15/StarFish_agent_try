import os
from dotenv import load_dotenv

load_dotenv()  # 自动读取项目根目录的 .env 文件

# LLM 配置
LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# Agent 配置
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 5))


def _parse_csv_env(name: str) -> list[str] | None:
	"""Parse comma-separated env var; empty -> None."""
	raw = os.getenv(name)
	if raw is None:
		return None
	raw = raw.strip()
	if not raw:
		return None
	return [part.strip() for part in raw.split(",") if part.strip()]


# Tool / Skill 管理
# - 不设置：使用内置默认全部启用
# - 设置为逗号分隔：只启用列出的项
ENABLED_TOOLS = _parse_csv_env("ENABLED_TOOLS")
ENABLED_SKILLS = _parse_csv_env("ENABLED_SKILLS")


# 文件式 skills（类似用 Markdown 维护一份“技能提示词”）
SKILL_DEFINITIONS_DIR = os.getenv("SKILL_DEFINITIONS_DIR", "skills/definitions")
LOAD_FILE_SKILLS = (os.getenv("LOAD_FILE_SKILLS", "0").strip().lower() in {"1", "true", "yes"})


# Skill 驱动的模型调优（可选）
_TEMP = os.getenv("SKILL_TEMPERATURE")
SKILL_TEMPERATURE = float(_TEMP) if _TEMP not in (None, "") else None
SKILL_MODEL = os.getenv("SKILL_MODEL") or None