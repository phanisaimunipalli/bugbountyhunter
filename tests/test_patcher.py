import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")


def test_patcher_returns_valid_patch():
    from agents.patcher import PatcherAgent
    agent = PatcherAgent(mock_mode=True)
    analysis = {
        "root_cause": "JSONDecodeError not re-raised as requests exception",
        "affected_files": ["requests/models.py"],
        "fix_approach": "Wrap json.loads in try/except and re-raise",
        "confidence_score": 0.91,
    }
    result = agent.run(analysis=analysis, repo_path="/tmp/fake", run_id="test")
    assert result is not None
    assert "patch_diff" in result
    assert "test_code" in result
    assert "explanation" in result
    assert "---" in result["patch_diff"] or "+++" in result["patch_diff"]


def test_patcher_result_with_failure_trace():
    from agents.patcher import PatcherAgent
    agent = PatcherAgent(mock_mode=True)
    analysis = {
        "root_cause": "Encoding error",
        "affected_files": ["lib/codec.py"],
        "fix_approach": "Add encoding fallback",
        "confidence_score": 0.85,
    }
    result = agent.run(
        analysis=analysis,
        repo_path="/tmp/fake",
        run_id="test",
        failure_trace="AssertionError: encoding expected utf-8 got None",
    )
    assert result is not None
    assert "patch_diff" in result
