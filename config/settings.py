import os
from pathlib import Path
from dotenv import load_dotenv

# 项目根目录（避免从 test/ 等子目录启动时，相对路径失效）
ROOT_DIR = Path(__file__).resolve().parents[1]

# 固定从项目内的 .env 读取（而不是依赖当前工作目录 CWD）
# 优先：config/.env（推荐把密钥放这里）
# 回退：项目根目录 .env（兼容旧用法）
_dotenv_candidates = [
	ROOT_DIR / "config" / ".env",
	ROOT_DIR / ".env",
]
for _path in _dotenv_candidates:
	if _path.exists():
		load_dotenv(dotenv_path=_path)
		break

# LLM 配置
LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# Agent 配置
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 5))

# Context 管理
# 以字符数粗略控制上下文大小（不依赖 tokenizer）
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", 120))
# 保留最近 N 条消息，其余进行压缩
CONTEXT_KEEP_LAST = int(os.getenv("CONTEXT_KEEP_LAST", 6))
# 压缩摘要的最大字符数
SUMMARY_MAX_CHARS = int(os.getenv("SUMMARY_MAX_CHARS", 1200))
# 打印上下文压缩调试日志
DEBUG_CONTEXT_COMPRESSION = (
	os.getenv("DEBUG_CONTEXT_COMPRESSION", "0").strip().lower() in {"1", "true", "yes"}
)


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
_skill_dir = os.getenv("SKILL_DEFINITIONS_DIR")
if _skill_dir and _skill_dir.strip():
	_skill_path = Path(_skill_dir.strip())
	if not _skill_path.is_absolute():
		_skill_path = ROOT_DIR / _skill_path
	SKILL_DEFINITIONS_DIR = str(_skill_path)
else:
	SKILL_DEFINITIONS_DIR = str(ROOT_DIR / "skills" / "definitions")
LOAD_FILE_SKILLS = (os.getenv("LOAD_FILE_SKILLS", "1").strip().lower() in {"1", "true", "yes"})


# Skill 驱动的模型调优（可选）
_TEMP = os.getenv("SKILL_TEMPERATURE")
SKILL_TEMPERATURE = float(_TEMP) if _TEMP not in (None, "") else None
SKILL_MODEL = os.getenv("SKILL_MODEL") or None