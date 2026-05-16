from openai import OpenAI
from config.settings import settings

TASK_MODEL_MAP = {
    "reasoning": "glm-4-plus",
    "classify": "qwen-turbo",
    "patch": "glm-4-plus",
    "default": "glm-4-plus",
}

MOCK_RESPONSES = {
    "reasoning": "I have analyzed the code. The root cause is in the exception handling path.",
    "classify": "0.88",
    "patch": "The fix applies a try/except block around the JSON decode call.",
    "default": "Mock LLM response.",
}


class LLMRouter:
    def __init__(self, mock_mode: bool | None = None):
        self.mock_mode = mock_mode if mock_mode is not None else settings.mock_mode
        if not self.mock_mode:
            self._client = OpenAI(
                api_key=settings.tokenrouter_api_key,
                base_url=settings.tokenrouter_base_url,
            )

    def complete(self, task: str, messages: list[dict], temperature: float = 0.2) -> str:
        if self.mock_mode:
            return MOCK_RESPONSES.get(task, MOCK_RESPONSES["default"])
        model = TASK_MODEL_MAP.get(task, TASK_MODEL_MAP["default"])
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
