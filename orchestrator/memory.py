import httpx
from config.settings import settings

# Shared in-process store for mock mode — all instances see the same data
_MOCK_STORE: dict = {}


class EvermindClient:
    def __init__(self, mock_mode: bool | None = None):
        self.mock_mode = mock_mode if mock_mode is not None else settings.mock_mode
        if not self.mock_mode:
            self._http = httpx.Client(
                base_url=settings.evermind_base_url,
                headers={"Authorization": f"Bearer {settings.evermind_api_key}"},
                timeout=10,
            )

    def store(self, key: str, value: object) -> None:
        if self.mock_mode:
            _MOCK_STORE[key] = value
            return
        self._http.post("/memory", json={"key": key, "value": value})

    def retrieve(self, key: str, default=None) -> object:
        if self.mock_mode:
            return _MOCK_STORE.get(key, default)
        resp = self._http.get(f"/memory/{key}")
        if resp.status_code == 404:
            return default
        return resp.json().get("value", default)

    def is_attempted(self, issue_url: str) -> bool:
        attempted: list = self.retrieve("attempted_issues", default=[])
        return issue_url in attempted

    def mark_attempted(self, issue_url: str, outcome: str) -> None:
        attempted: list = self.retrieve("attempted_issues", default=[])
        if issue_url not in attempted:
            attempted.append(issue_url)
        self.store("attempted_issues", attempted)
        history: list = self.retrieve("run_history", default=[])
        history.append({"issue_url": issue_url, "outcome": outcome})
        self.store("run_history", history)
