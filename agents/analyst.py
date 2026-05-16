import json
import os
from pathlib import Path
from config.settings import settings
from config.mocks import MOCK_ANALYST_RESULT
from router.llm import LLMRouter
from terminal.server import emit_event

CONFIDENCE_THRESHOLD = 0.70


def _collect_file_tree(repo_path: str, max_files: int = 80) -> str:
    lines = []
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules", ".git")]
        for f in files:
            if f.endswith(".py"):
                rel = os.path.relpath(os.path.join(root, f), repo_path)
                lines.append(rel)
                if len(lines) >= max_files:
                    return "\n".join(lines)
    return "\n".join(lines)


def _read_file_snippet(repo_path: str, rel_path: str, max_chars: int = 2000) -> str:
    full = Path(repo_path) / rel_path
    if not full.exists():
        return ""
    return full.read_text(errors="replace")[:max_chars]


class AnalystAgent:
    def __init__(self, mock_mode: bool | None = None):
        self.mock_mode = mock_mode if mock_mode is not None else settings.mock_mode
        self.llm = LLMRouter()
        self._force_confidence: float | None = None

    def run(self, issue: dict, repo_path: str, run_id: str = "") -> dict | None:
        emit_event("ANALYST", "GLM-5.1 reading issue + file tree", run_id)

        if self.mock_mode:
            result = dict(MOCK_ANALYST_RESULT)
            if self._force_confidence is not None:
                result["confidence_score"] = self._force_confidence
            if result["confidence_score"] < CONFIDENCE_THRESHOLD:
                emit_event("ANALYST", f"✗ confidence {result['confidence_score']:.2f} below threshold — skipping", run_id)
                return None
            emit_event("ANALYST", f"Root cause: {result['affected_files'][0]} identified", run_id)
            emit_event("ANALYST", f"confidence: {result['confidence_score']:.2f}  ✓ proceeding", run_id)
            return result

        file_tree = _collect_file_tree(repo_path)
        snippets = "\n\n".join(
            f"=== {f} ===\n{_read_file_snippet(repo_path, f)}"
            for f in file_tree.splitlines()[:5]
        )

        prompt = f"""You are a senior Python engineer. Analyze this GitHub issue and the repository structure.

Issue Title: {issue['issue_title']}
Issue Body: {issue['issue_body'][:1200]}

Repository file tree (Python files):
{file_tree[:3000]}

Key file snippets:
{snippets[:4000]}

Return a JSON object with exactly these keys:
- root_cause: string describing the bug root cause
- affected_files: list of relative file paths that need changes
- fix_approach: string describing the precise fix
- confidence_score: float 0.0-1.0 (how confident you are this is fixable)

Reply with ONLY valid JSON, no markdown fences."""

        raw = self.llm.complete("reasoning", [{"role": "user", "content": prompt}])
        try:
            result = json.loads(raw.strip())
            result["confidence_score"] = float(result.get("confidence_score", 0.5))
        except Exception:
            return None

        if result["confidence_score"] < CONFIDENCE_THRESHOLD:
            emit_event("ANALYST", f"✗ confidence {result['confidence_score']:.2f} below threshold — skipping", run_id)
            return None

        emit_event("ANALYST", f"Root cause: {', '.join(result['affected_files'])}", run_id)
        emit_event("ANALYST", f"confidence: {result['confidence_score']:.2f}  ✓ proceeding", run_id)
        return result
