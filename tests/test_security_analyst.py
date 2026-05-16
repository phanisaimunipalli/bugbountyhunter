import os

os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")


def test_security_analyst_mock_returns_findings():
    from agents.security_analyst import SecurityAnalystAgent

    agent = SecurityAnalystAgent(mock_mode=True)
    issue = {
        "issue_title": "JSONDecodeError not caught",
        "issue_body": "response.json() raises wrong exception",
    }
    result = agent.run(issue=issue, repo_path="/fake", run_id="sec-001")
    assert result is not None
    assert result["total_vulns"] >= 1
    assert result["findings"][0]["vuln_class"] == "injection"
    assert result["findings"][0]["confidence"] >= 0.6


def test_security_analyst_severity_summary():
    from agents.security_analyst import SecurityAnalystAgent

    agent = SecurityAnalystAgent(mock_mode=True)
    issue = {"issue_title": "test", "issue_body": "test"}
    result = agent.run(issue=issue, repo_path="/fake", run_id="sec-002")
    assert result["severity_summary"]["high"] == 1
    assert result["severity_summary"]["critical"] == 0
