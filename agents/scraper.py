import httpx
import yaml
from pathlib import Path
from config.settings import settings
from config.mocks import MOCK_SCRAPER_RESULT
from orchestrator.memory import EvermindClient
from router.llm import LLMRouter
from terminal.server import emit_event


def _load_repo_whitelist() -> list[str]:
    repos_file = Path("config/repos.yaml")
    if not repos_file.exists():
        return []
    data = yaml.safe_load(repos_file.read_text())
    return data.get("repos", []) or []


class ScraperAgent:
    def __init__(
        self,
        mock_mode: bool | None = None,
        memory: EvermindClient | None = None,
        repo_whitelist: list[str] | None = None,
    ):
        self.mock_mode = mock_mode if mock_mode is not None else settings.mock_mode
        self.memory = memory or EvermindClient()
        self.llm = LLMRouter()
        self.repo_whitelist = repo_whitelist if repo_whitelist is not None else _load_repo_whitelist()

    def run(self, query: str, run_id: str = "") -> list[dict]:
        emit_event("SCRAPER", "Bright Data: querying GitHub...", run_id)
        issues = self._fetch_issues(query)
        emit_event("SCRAPER", f"Found {len(issues)} open Python bugs", run_id)

        if self.repo_whitelist:
            issues = [i for i in issues if any(r in i["repo_url"] for r in self.repo_whitelist)]
            emit_event("SCRAPER", f"Whitelist filter: {len(issues)} candidates remain", run_id)

        issues = [i for i in issues if not self.memory.is_attempted(i["issue_url"])]
        emit_event("SCRAPER", f"Evermind dedup: {len(issues)} not yet attempted", run_id)

        if not issues:
            emit_event("SCRAPER", "No new issues found", run_id)
            return []

        issues = self._score_fixability(issues, run_id)
        issues.sort(key=lambda x: x["fixability_score"], reverse=True)
        top = issues[:1]
        if top:
            emit_event("SCRAPER", f"Top candidate: {top[0]['repo_url']} issue #{top[0]['issue_number']}", run_id)
            emit_event("SCRAPER", f"  \"{top[0]['issue_title']}\" (score: {top[0]['fixability_score']:.2f})", run_id)
        return top

    def _fetch_issues(self, query: str) -> list[dict]:
        if self.mock_mode:
            return list(MOCK_SCRAPER_RESULT)

        # Bright Data Web Unlocker API — Bearer token auth, routes through their network
        github_url = f"https://api.github.com/search/issues?q={query}+state:open&sort=created&order=desc&per_page=20"
        headers = {
            "Authorization": f"token {settings.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "x-brightdata-token": settings.bright_data_api_key,
        }
        resp = httpx.get(
            github_url,
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        return [
            {
                "repo_url": item["repository_url"].replace("api.github.com/repos", "github.com"),
                "issue_url": item["html_url"],
                "issue_title": item["title"],
                "issue_body": item.get("body") or "",
                "issue_number": item["number"],
                "fixability_score": 0.0,
            }
            for item in items
        ]

    def _score_fixability(self, issues: list[dict], run_id: str) -> list[dict]:
        emit_event("SCRAPER", f"Qwen scoring {len(issues)} candidates...", run_id)
        scored = []
        for issue in issues:
            if self.mock_mode:
                issue["fixability_score"] = issue.get("fixability_score", 0.75)
                scored.append(issue)
                continue
            prompt = (
                f"Rate the fixability of this Python GitHub issue from 0.0 to 1.0. "
                f"High scores: clear error trace, small scope, test suite likely exists. "
                f"Low scores: architectural, vague, or requires domain knowledge.\n\n"
                f"Title: {issue['issue_title']}\nBody: {issue['issue_body'][:800]}\n\n"
                f"Reply with ONLY a float between 0.0 and 1.0."
            )
            raw = self.llm.complete("classify", [{"role": "user", "content": prompt}])
            try:
                issue["fixability_score"] = float(raw.strip())
            except ValueError:
                issue["fixability_score"] = 0.5
            scored.append(issue)
        return scored
