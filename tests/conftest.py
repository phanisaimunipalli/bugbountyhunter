import pytest


@pytest.fixture(autouse=True)
def reset_mock_store():
    from orchestrator import memory
    memory._MOCK_STORE.clear()
    yield
    memory._MOCK_STORE.clear()
