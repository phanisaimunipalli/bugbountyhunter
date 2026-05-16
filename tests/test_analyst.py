import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")


def test_analyst_returns_valid_analysis():
    from agents.analyst import AnalystAgent
    agent = AnalystAgent(mock_mode=True)
    issue = {
        "repo_url": "https://github.com/psf/requests",
        "issue_title": "JSONDecodeError not caught",
        "issue_body": "When calling response.json() on invalid JSON...",
        "issue_number": 6821,
    }
    result = agent.run(issue=issue, repo_path="/tmp/fake_repo", run_id="test")
    assert result is not None
    assert "root_cause" in result
    assert "affected_files" in result
    assert "confidence_score" in result
    assert isinstance(result["confidence_score"], float)


def test_analyst_rejects_low_confidence():
    from agents.analyst import AnalystAgent
    agent = AnalystAgent(mock_mode=True)
    agent._force_confidence = 0.3
    issue = {
        "repo_url": "https://github.com/psf/requests",
        "issue_title": "vague issue",
        "issue_body": "something is wrong",
        "issue_number": 9999,
    }
    result = agent.run(issue=issue, repo_path="/tmp/fake_repo", run_id="test")
    assert result is None
