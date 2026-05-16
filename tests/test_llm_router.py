import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")


def test_router_returns_string_in_mock_mode():
    from router.llm import LLMRouter
    router = LLMRouter(mock_mode=True)
    result = router.complete(
        task="classify",
        messages=[{"role": "user", "content": "hello"}],
    )
    assert isinstance(result, str)
    assert len(result) > 0


def test_router_selects_glm_for_reasoning():
    from router.llm import TASK_MODEL_MAP
    assert TASK_MODEL_MAP["reasoning"] == "glm-4-plus"
    assert TASK_MODEL_MAP["classify"] == "qwen-turbo"
