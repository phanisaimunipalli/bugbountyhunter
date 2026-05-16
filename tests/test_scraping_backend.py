import os

os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")


def test_scraping_backend_imports():
    """Verify Scrapling backend module loads without errors."""
    from agents._scraping_backend import fetch_github_api, fetch_issue_page
    assert callable(fetch_github_api)
    assert callable(fetch_issue_page)


def test_scrapling_available():
    """Scrapling should be importable in this environment."""
    from agents._scraping_backend import _HAS_SCRAPLING
    assert _HAS_SCRAPLING is True


def test_scraper_agent_uses_backend():
    """ScraperAgent in mock mode still works with new backend wiring."""
    from agents.scraper import ScraperAgent
    agent = ScraperAgent(mock_mode=True)
    result = agent.run(query="label:bug", run_id="backend-001")
    assert len(result) == 1
    assert result[0]["repo_url"].startswith("https://github.com")
