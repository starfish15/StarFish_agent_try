import os
from dotenv import load_dotenv

load_dotenv()  # 自动读取项目根目录的 .env 文件

# LLM 配置
LLM_API_KEY = os.getenv("DEEPSEEK_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# Agent 配置
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", 5))