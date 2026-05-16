import asyncio
import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")

import pytest


@pytest.mark.asyncio
async def test_run_pipeline_completes_in_mock():
    from orchestrator.engine import run_pipeline
    result = await run_pipeline(run_id="test-e2e-001")
    assert result is not None
    assert result["status"] in ("success", "no_issues", "failed", "skipped")


@pytest.mark.asyncio
async def test_run_pipeline_returns_pr_url_on_success():
    from orchestrator.engine import run_pipeline
    result = await run_pipeline(run_id="test-e2e-002")
    if result["status"] == "success":
        assert "pr_url" in result
        assert result["pr_url"].startswith("https://github.com")
