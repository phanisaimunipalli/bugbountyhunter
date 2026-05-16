from pathlib import Path
from config.settings import settings
from config.mocks import MOCK_PATCH_RESULT
from router.llm import LLMRouter
from terminal.server import emit_event


def _read_affected_files(repo_path: str, affected_files: list[str], max_chars: int = 3000) -> str:
    parts = []
    for rel in affected_files:
        full = Path(repo_path) / rel
        if full.exists():
            content = full.read_text(errors="replace")[:max_chars]
            parts.append(f"=== {rel} ===\n{content}")
    return "\n\n".join(parts)


class PatcherAgent:
    def __init__(self, mock_mode: bool | None = None):
        self.mock_mode = mock_mode if mock_mode is not None else settings.mock_mode
        self.llm = LLMRouter()

    def run(
        self,
        analysis: dict,
        repo_path: str,
        run_id: str = "",
        failure_trace: str | None = None,
    ) -> dict | None:
        emit_event("PATCHER", "Convening Expert Panel (Senior Engineer + Test Writer)...", run_id)

        if self.mock_mode:
            emit_event("PATCHER", "→ Senior Engineer analyzing patch", run_id)
            emit_event("PATCHER", "→ Test Writer extending test suite", run_id)
            patch = dict(MOCK_PATCH_RESULT)
            added = patch["patch_diff"].count("\n+")
            removed = patch["patch_diff"].count("\n-")
            emit_event("PATCHER", f"Patch ready: +{added} lines / -{removed} lines", run_id)
            return patch

        file_contents = _read_affected_files(repo_path, analysis.get("affected_files", []))
        failure_section = f"\n\nPrevious patch failed with:\n{failure_trace}" if failure_trace else ""

        senior_prompt = f"""You are a Senior Python Engineer on an expert panel.

Bug root cause: {analysis['root_cause']}
Fix approach: {analysis['fix_approach']}
{failure_section}

Affected file(s):
{file_contents}

Write a minimal, precise git diff patch that fixes ONLY this bug. Do not refactor unrelated code.
Return ONLY a valid unified diff (--- a/... +++ b/... format). No markdown, no explanation."""

        emit_event("PATCHER", "→ Senior Engineer writing patch", run_id)
        patch_diff = self.llm.complete("patch", [{"role": "user", "content": senior_prompt}])

        test_prompt = f"""You are a Test Writer on an expert panel.

A patch was just written to fix: {analysis['root_cause']}

Patch:
{patch_diff[:2000]}

Write a pytest test function that verifies this fix. Use only the standard library and pytest.
Return ONLY the Python test function code, no imports (assume pytest is imported), no explanation."""

        emit_event("PATCHER", "→ Test Writer extending test suite", run_id)
        test_code = self.llm.complete("patch", [{"role": "user", "content": test_prompt}])

        added = sum(1 for ln in patch_diff.splitlines() if ln.startswith("+") and not ln.startswith("+++"))
        removed = sum(1 for ln in patch_diff.splitlines() if ln.startswith("-") and not ln.startswith("---"))
        emit_event("PATCHER", f"Patch ready: +{added} lines / -{removed} lines", run_id)

        return {
            "patch_diff": patch_diff,
            "test_code": test_code,
            "explanation": analysis["fix_approach"],
        }
