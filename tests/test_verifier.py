import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")


def test_verifier_returns_passed_in_mock():
    from agents.verifier import VerifierAgent
    agent = VerifierAgent(mock_mode=True)
    result = agent.run(
        patch={"patch_diff": "--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new", "test_code": "", "explanation": ""},
        repo_path="/tmp/fake",
        run_id="test",
    )
    assert result["passed"] is True
    assert "test_output" in result
    assert result["retry_count"] == 0


def test_verifier_result_has_retry_count():
    from agents.verifier import VerifierAgent
    agent = VerifierAgent(mock_mode=True)
    result = agent.run(
        patch={"patch_diff": "", "test_code": "", "explanation": ""},
        repo_path="/tmp/fake",
        run_id="test",
    )
    assert "retry_count" in result
