import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")


def test_settings_loads_mock_mode(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "true")
    monkeypatch.setenv("GITHUB_TOKEN", "fake")
    monkeypatch.setenv("GITHUB_USERNAME", "fake")
    from config.settings import Settings
    s = Settings()
    assert s.mock_mode is True


def test_mock_scraper_result_is_valid():
    from config.mocks import MOCK_SCRAPER_RESULT
    assert "repo_url" in MOCK_SCRAPER_RESULT[0]
    assert "issue_number" in MOCK_SCRAPER_RESULT[0]
