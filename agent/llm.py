from openai import OpenAI
from config.settings import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

class LLMClient:
    def __init__(self):
        self._api_key = LLM_API_KEY
        self._base_url = LLM_BASE_URL
        self.client: OpenAI | None = None
        self.model = LLM_MODEL

    def _get_client(self) -> OpenAI:
        if self.client is None:
            if not self._api_key:
                raise ValueError(
                    "缺少 API Key：请在 .env 中设置 DEEPSEEK_API_KEY（或在环境变量中设置）。"
                )
            self.client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self.client

    def chat(self, messages, temperature: float = 0.0, model: str | None = None, **kwargs):
        client = self._get_client()
        response = client.chat.completions.create(
            model=model or self.model,
            messages=messages,
            temperature=temperature,
            **kwargs,
        )
        return response.choices[0].message.content