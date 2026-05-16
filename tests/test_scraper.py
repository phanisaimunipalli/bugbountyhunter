import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")


def test_scraper_returns_list_of_issues():
    from agents.scraper import ScraperAgent
    agent = ScraperAgent(mock_mode=True)
    results = agent.run(query="label:bug language:python")
    assert isinstance(results, list)
    assert len(results) > 0


def test_scraper_result_has_required_fields():
    from agents.scraper import ScraperAgent
    agent = ScraperAgent(mock_mode=True)
    results = agent.run(query="label:bug language:python")
    issue = results[0]
    for field in ("repo_url", "issue_url", "issue_title", "issue_body", "issue_number", "fixability_score"):
        assert field in issue, f"missing field: {field}"


def test_scraper_deduplicates_via_evermind():
    from agents.scraper import ScraperAgent
    from orchestrator.memory import EvermindClient
    memory = EvermindClient(mock_mode=True)
    memory.mark_attempted("https://github.com/psf/requests/issues/6821", outcome="success")
    agent = ScraperAgent(mock_mode=True, memory=memory)
    results = agent.run(query="label:bug language:python")
    urls = [r["issue_url"] for r in results]
    assert "https://github.com/psf/requests/issues/6821" not in urls


def test_scraper_applies_repo_whitelist():
    from agents.scraper import ScraperAgent
    agent = ScraperAgent(mock_mode=True, repo_whitelist=["encode/httpx"])
    results = agent.run(query="label:bug language:python")
    for r in results:
        assert "encode/httpx" in r["repo_url"]
