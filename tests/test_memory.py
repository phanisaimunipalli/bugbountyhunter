import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")


def test_store_and_retrieve_in_mock():
    from orchestrator.memory import EvermindClient
    client = EvermindClient(mock_mode=True)
    client.store("attempted_issues", ["https://github.com/psf/requests/issues/6821"])
    result = client.retrieve("attempted_issues")
    assert "https://github.com/psf/requests/issues/6821" in result


def test_is_attempted_returns_true_for_stored():
    from orchestrator.memory import EvermindClient
    client = EvermindClient(mock_mode=True)
    client.store("attempted_issues", ["https://github.com/foo/bar/issues/1"])
    assert client.is_attempted("https://github.com/foo/bar/issues/1") is True


def test_is_attempted_returns_false_for_new():
    from orchestrator.memory import EvermindClient
    client = EvermindClient(mock_mode=True)
    assert client.is_attempted("https://github.com/new/repo/issues/99") is False


def test_mark_attempted_persists():
    from orchestrator.memory import EvermindClient
    client = EvermindClient(mock_mode=True)
    client.mark_attempted("https://github.com/x/y/issues/5", outcome="success")
    assert client.is_attempted("https://github.com/x/y/issues/5") is True
