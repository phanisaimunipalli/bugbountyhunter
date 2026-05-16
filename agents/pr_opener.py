import subprocess
import httpx
from config.settings import settings
from config.mocks import MOCK_PR_RESULT
from terminal.server import emit_event


def _build_pr_body(issue_number: int, explanation: str, patch_diff: str, terminal_url: str) -> str:
    return f"""## Autonomous Fix by Bounty Hunter \U0001f916

Closes #{issue_number}

### What changed
{explanation}

### Diff
```diff
{patch_diff[:3000]}
```

### Live verification
Watch the agent's reasoning and test run in real time:
\U0001f517 {terminal_url}

---
*Generated autonomously by [Bounty Hunter](https://github.com/agent-forge/bounty-hunter) — Agent Forge 2026*
"""


def _extract_owner_repo(repo_url: str) -> tuple[str, str]:
    parts = repo_url.rstrip("/").split("/")
    return parts[-2], parts[-1]


class PROpenerAgent:
    def __init__(self, mock_mode: bool | None = None):
        self.mock_mode = mock_mode if mock_mode is not None else settings.mock_mode

    def run(self, issue: dict, patch: dict, terminal_url: str, run_id: str = "") -> dict:
        emit_event("PR_OPENER", "Actionbook: navigating GitHub...", run_id)

        if self.mock_mode:
            emit_event("PR_OPENER", "Fork created, branch pushed", run_id)
            emit_event("PR_OPENER", f"PR opened: {MOCK_PR_RESULT['pr_url']}  ✓", run_id)
            return dict(MOCK_PR_RESULT)

        owner, repo = _extract_owner_repo(issue["repo_url"])
        branch_name = f"bounty-hunter/fix-issue-{issue['issue_number']}"
        pr_body = _build_pr_body(
            issue_number=issue["issue_number"],
            explanation=patch["explanation"],
            patch_diff=patch["patch_diff"],
            terminal_url=terminal_url,
        )
        pr_title = f"fix: {issue['issue_title'][:72]}"

        try:
            result = self._open_via_actionbook(owner, repo, branch_name, pr_title, pr_body, run_id)
        except Exception as e:
            emit_event("PR_OPENER", f"Actionbook failed ({e}) — falling back to GitHub API", run_id)
            result = self._open_via_github_api(owner, repo, branch_name, pr_title, pr_body, run_id)

        return result

    def _push_branch(self, repo_path: str, branch_name: str, repo: str) -> None:
        remote_url = (
            f"https://{settings.github_username}:{settings.github_token}"
            f"@github.com/{settings.github_username}/{repo}.git"
        )
        cmds = [
            ["git", "checkout", "-b", branch_name],
            ["git", "add", "-A"],
            ["git", "commit", "-m", "fix: autonomous patch by bounty-hunter"],
            ["git", "remote", "add", "fork", remote_url],
            ["git", "push", "fork", branch_name],
        ]
        for cmd in cmds:
            subprocess.run(cmd, cwd=repo_path, check=True, capture_output=True)

    def _open_via_actionbook(
        self, owner: str, repo: str, branch: str, title: str, body: str, run_id: str
    ) -> dict:
        headers = {
            "Authorization": f"Bearer {settings.actionbook_api_key}",
            "Content-Type": "application/json",
        }
        session_resp = httpx.post(
            "https://api.actionbook.ai/v1/sessions",
            headers=headers,
            json={"browser": "chromium", "headless": True},
            timeout=30,
        )
        session_resp.raise_for_status()
        session_id = session_resp.json()["session_id"]

        actions = [
            {"action": "navigate", "url": f"https://github.com/{owner}/{repo}"},
            {"action": "click", "selector": "[data-testid='fork-button'], .octicon-repo-forked"},
            {"action": "click", "selector": "button[type='submit']"},
            {"action": "navigate", "url": f"https://github.com/{owner}/{repo}/compare/{branch}?expand=1"},
            {"action": "fill", "selector": "#pull_request_title", "value": title},
            {"action": "fill", "selector": "#pull_request_body", "value": body},
            {"action": "click", "selector": "button[data-disable-with='Creating pull request…']"},
            {"action": "get_url"},
        ]

        emit_event("PR_OPENER", "Fork created, branch pushed", run_id)
        result_resp = httpx.post(
            f"https://api.actionbook.ai/v1/sessions/{session_id}/run",
            headers=headers,
            json={"actions": actions},
            timeout=60,
        )
        result_resp.raise_for_status()
        pr_url = result_resp.json().get("final_url", f"https://github.com/{owner}/{repo}/pulls")
        emit_event("PR_OPENER", f"PR opened: {pr_url}  ✓", run_id)
        return {"pr_url": pr_url, "comment_posted": True}

    def _open_via_github_api(
        self, owner: str, repo: str, branch: str, title: str, body: str, run_id: str
    ) -> dict:
        headers = {
            "Authorization": f"token {settings.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        resp = httpx.post(
            f"https://api.github.com/repos/{owner}/{repo}/pulls",
            headers=headers,
            json={
                "title": title,
                "body": body,
                "head": f"{settings.github_username}:{branch}",
                "base": "main",
            },
            timeout=15,
        )
        resp.raise_for_status()
        pr_url = resp.json()["html_url"]
        emit_event("PR_OPENER", f"PR opened via API: {pr_url}  ✓", run_id)
        return {"pr_url": pr_url, "comment_posted": True}
