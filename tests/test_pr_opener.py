import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")


def test_pr_opener_returns_pr_url_in_mock():
    from agents.pr_opener import PROpenerAgent
    agent = PROpenerAgent(mock_mode=True)
    result = agent.run(
        issue={"repo_url": "https://github.com/psf/requests", "issue_number": 6821, "issue_title": "bug"},
        patch={"patch_diff": "--- a/x\n+++ b/x", "explanation": "fix it", "test_code": ""},
        terminal_url="https://bh.zeabur.app",
        run_id="test",
    )
    assert "pr_url" in result
    assert result["pr_url"].startswith("https://github.com")
    assert result["comment_posted"] is True


def test_pr_opener_pr_body_contains_terminal_url():
    from agents.pr_opener import _build_pr_body
    body = _build_pr_body(
        issue_number=42,
        explanation="Wrap json.loads in try/except",
        patch_diff="--- a/x\n+++ b/x",
        terminal_url="https://bh.zeabur.app",
    )
    assert "https://bh.zeabur.app" in body
    assert "42" in body
    assert "Wrap json.loads" in body
