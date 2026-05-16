"""
SecurityAnalystAgent — Shannon-inspired vulnerability analysis.

Borrows Shannon's methodology: white-box source code analysis with
structured vuln classification (injection, xss, ssrf, auth, authz).
Produces actionable findings with proof-of-concept suggestions.

Shannon (https://github.com/KeygraphHQ/shannon) is the reference architecture.
We adapt its prompt patterns for our Python-based pipeline.
"""
import json
import os
from pathlib import Path
from config.settings import settings
from config.mocks import MOCK_SECURITY_RESULT
from router.llm import LLMRouter
from terminal.server import emit_event

VULN_CLASSES = ("injection", "xss", "ssrf", "auth", "path_traversal")

CONFIDENCE_THRESHOLD = 0.60


def _collect_python_sources(repo_path: str, max_files: int = 30, max_chars: int = 2000) -> str:
    """Collect Python source snippets from repo, prioritizing security-sensitive files."""
    priority_patterns = ("auth", "login", "api", "view", "route", "handler", "model", "db", "sql")
    files_found: list[tuple[str, str]] = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "node_modules", ".git", "venv")]
        for f in files:
            if not f.endswith(".py"):
                continue
            rel = os.path.relpath(os.path.join(root, f), repo_path)
            content = Path(os.path.join(root, f)).read_text(errors="replace")[:max_chars]
            files_found.append((rel, content))
            if len(files_found) >= max_files * 2:
                break

    # Sort: security-sensitive files first
    def _priority(item: tuple[str, str]) -> int:
        name = item[0].lower()
        return 0 if any(p in name for p in priority_patterns) else 1

    files_found.sort(key=_priority)
    files_found = files_found[:max_files]

    parts = [f"=== {rel} ===\n{content}" for rel, content in files_found]
    return "\n\n".join(parts)


class SecurityAnalystAgent:
    """Analyzes cloned repo for security vulnerabilities using Shannon's methodology."""

    def __init__(self, mock_mode: bool | None = None):
        self.mock_mode = mock_mode if mock_mode is not None else settings.mock_mode
        self.llm = LLMRouter()

    def run(self, issue: dict, repo_path: str, run_id: str = "") -> dict | None:
        """Run security analysis on the repo. Returns findings or None if nothing found."""
        emit_event("SECURITY", "Shannon-style white-box vuln scan starting...", run_id)

        if self.mock_mode:
            emit_event("SECURITY", f"Found {len(MOCK_SECURITY_RESULT['findings'])} potential vulnerabilities", run_id)
            return dict(MOCK_SECURITY_RESULT)

        sources = _collect_python_sources(repo_path)
        if not sources.strip():
            emit_event("SECURITY", "No Python sources found — skipping", run_id)
            return None

        findings = self._analyze_vuln_classes(issue, sources, run_id)

        if not findings:
            emit_event("SECURITY", "No actionable vulnerabilities found", run_id)
            return None

        result = {
            "findings": findings,
            "total_vulns": len(findings),
            "severity_summary": self._summarize_severity(findings),
        }
        emit_event("SECURITY", f"Analysis complete: {len(findings)} findings across {len(set(f['vuln_class'] for f in findings))} categories", run_id)
        return result

    def _analyze_vuln_classes(self, issue: dict, sources: str, run_id: str) -> list[dict]:
        """Analyze all vuln classes in one LLM call to save tokens."""
        emit_event("SECURITY", "Analyzing: injection, xss, ssrf, auth, path_traversal...", run_id)

        prompt = f"""You are a security analyst performing white-box vulnerability analysis.
Analyze this Python source code for security vulnerabilities.

Context — this repo has an open bug report:
Title: {issue['issue_title']}
Body: {issue['issue_body'][:600]}

Source code:
{sources[:6000]}

For each vulnerability found, classify it into one of: {', '.join(VULN_CLASSES)}

Return a JSON array of findings. Each finding must have:
- "vuln_class": one of {list(VULN_CLASSES)}
- "severity": "critical" | "high" | "medium" | "low"
- "file": relative file path
- "line_hint": approximate line number or range
- "description": what the vulnerability is (1-2 sentences)
- "proof_of_concept": minimal PoC or payload suggestion
- "fix_suggestion": how to fix it (1-2 sentences)
- "confidence": float 0.0-1.0

Return ONLY a valid JSON array. Empty array if no vulns found. No markdown."""

        raw = self.llm.complete("reasoning", [{"role": "user", "content": prompt}])
        try:
            findings = json.loads(raw.strip())
            if not isinstance(findings, list):
                return []
            # Filter low-confidence noise
            return [f for f in findings if f.get("confidence", 0) >= CONFIDENCE_THRESHOLD]
        except (json.JSONDecodeError, TypeError):
            emit_event("SECURITY", "LLM returned unparseable response — skipping", run_id)
            return []

    def _summarize_severity(self, findings: list[dict]) -> dict:
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in findings:
            sev = f.get("severity", "low")
            if sev in summary:
                summary[sev] += 1
        return summary
