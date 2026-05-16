import asyncio
import os
import tempfile
from config.settings import settings
from orchestrator.memory import EvermindClient
from agents.scraper import ScraperAgent
from agents.analyst import AnalystAgent
from agents.patcher import PatcherAgent
from agents.verifier import VerifierAgent
from agents.pr_opener import PROpenerAgent
from sandbox.runner import SandboxRunner
from terminal.server import emit_event

MAX_RETRIES = 2


async def run_pipeline(run_id: str) -> dict:
    emit_event("ORCHESTRATOR", f"Pipeline start — run {run_id}", run_id)

    terminal_url = os.environ.get("TERMINAL_URL", settings.terminal_url)

    memory = EvermindClient()
    scraper = ScraperAgent(memory=memory)
    analyst = AnalystAgent()
    patcher = PatcherAgent()
    verifier = VerifierAgent()
    pr_opener = PROpenerAgent()

    issues = await asyncio.to_thread(
        scraper.run, query="label:bug language:python", run_id=run_id
    )
    if not issues:
        emit_event("ORCHESTRATOR", "No viable issues found — halting", run_id)
        return {"status": "no_issues", "run_id": run_id}

    issue = issues[0]
    sandbox = SandboxRunner(run_id=run_id)
    try:
        emit_event("ANALYST", f"Cloning {issue['repo_url']} to sandbox...", run_id)
        if settings.mock_mode:
            repo_path = tempfile.mkdtemp(prefix=f"bh_{run_id}_")
        else:
            repo_path = await asyncio.to_thread(sandbox.clone, issue["repo_url"])

        analysis = await asyncio.to_thread(
            analyst.run, issue=issue, repo_path=repo_path, run_id=run_id
        )
        if analysis is None:
            memory.mark_attempted(issue["issue_url"], outcome="skipped_low_confidence")
            emit_event("ORCHESTRATOR", "Issue skipped — low confidence. Run again for next candidate.", run_id)
            return {"status": "skipped", "run_id": run_id, "issue": issue["issue_url"]}

        patch = await asyncio.to_thread(
            patcher.run, analysis=analysis, repo_path=repo_path, run_id=run_id
        )
        if patch is None:
            return {"status": "failed", "run_id": run_id, "reason": "patcher returned None"}

        verification = None
        for attempt in range(MAX_RETRIES + 1):
            verification = await asyncio.to_thread(
                verifier.run, patch=patch, repo_path=repo_path, run_id=run_id, retry_count=attempt
            )
            if verification["passed"]:
                break
            if attempt < MAX_RETRIES:
                emit_event("VERIFIER", f"Retrying patch (attempt {attempt + 2}/{MAX_RETRIES + 1})...", run_id)
                patch = await asyncio.to_thread(
                    patcher.run,
                    analysis=analysis,
                    repo_path=repo_path,
                    run_id=run_id,
                    failure_trace=verification["test_output"],
                )
                if patch is None:
                    break

        if not verification or not verification["passed"]:
            memory.mark_attempted(issue["issue_url"], outcome="failed_verification")
            emit_event("ORCHESTRATOR", "✗ Could not produce a passing patch — marking issue as too complex", run_id)
            return {"status": "failed", "run_id": run_id, "reason": "verification failed"}

        pr_result = await asyncio.to_thread(
            pr_opener.run,
            issue=issue,
            patch=patch,
            terminal_url=terminal_url,
            run_id=run_id,
        )

        memory.mark_attempted(issue["issue_url"], outcome="success")
        emit_event("COMPLETE", f"Run {run_id} finished  ✓  PR: {pr_result['pr_url']}", run_id)
        return {
            "status": "success",
            "run_id": run_id,
            "pr_url": pr_result["pr_url"],
            "issue_url": issue["issue_url"],
        }

    finally:
        if not settings.mock_mode:
            sandbox.cleanup()
