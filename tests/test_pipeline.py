import asyncio
import os
os.environ["MOCK_MODE"] = "true"
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")

import pytest


@pytest.mark.asyncio
async def test_full_pipeline_mock_mode():
    from orchestrator.engine import run_pipeline
    result = await run_pipeline(run_id="integration-001")
    assert result["status"] == "success"
    assert result["pr_url"].startswith("https://github.com")
    assert result["issue_url"].startswith("https://github.com")


@pytest.mark.asyncio
async def test_pipeline_emits_events():
    from terminal.server import _event_buffer
    initial_len = len(_event_buffer)
    from orchestrator.engine import run_pipeline
    await run_pipeline(run_id="integration-002")
    new_events = _event_buffer[initial_len:]
    agents_seen = {e["agent"] for e in new_events}
    assert "SCRAPER" in agents_seen
    assert "ANALYST" in agents_seen
    assert "PATCHER" in agents_seen
    assert "VERIFIER" in agents_seen
    assert "PR_OPENER" in agents_seen
    assert "COMPLETE" in agents_seen


@pytest.mark.asyncio
async def test_evermind_records_run():
    from orchestrator.engine import run_pipeline
    await run_pipeline(run_id="integration-003")
    from orchestrator.memory import EvermindClient
    from config.mocks import MOCK_SCRAPER_RESULT
    memory = EvermindClient(mock_mode=True)
    issue_url = MOCK_SCRAPER_RESULT[0]["issue_url"]
    assert memory.is_attempted(issue_url)
