import httpx
import time
from config.settings import settings
from config.mocks import MOCK_VERIFIER_RESULT
from sandbox.runner import SandboxRunner
from terminal.server import emit_event


class VerifierAgent:
    def __init__(self, mock_mode: bool | None = None):
        self.mock_mode = mock_mode if mock_mode is not None else settings.mock_mode

    def run(self, patch: dict, repo_path: str, run_id: str = "", retry_count: int = 0) -> dict:
        emit_event("VERIFIER", "Submitting to Nosana GPU node...", run_id)

        if self.mock_mode:
            emit_event("VERIFIER", f"pytest: {MOCK_VERIFIER_RESULT['test_output']}  ✓", run_id)
            return {**MOCK_VERIFIER_RESULT, "retry_count": retry_count}

        runner = SandboxRunner(run_id=run_id)
        try:
            runner.apply_patch(repo_path, patch["patch_diff"])
        except RuntimeError as e:
            emit_event("VERIFIER", f"✗ patch apply failed: {e}", run_id)
            return {"passed": False, "test_output": str(e), "retry_count": retry_count}

        result = self._run_on_nosana(repo_path, run_id)
        if result is None:
            emit_event("VERIFIER", "Nosana unavailable — falling back to local runner", run_id)
            result = runner.run_tests_in_dir(repo_path)

        result["retry_count"] = retry_count
        if result["passed"]:
            last_line = result["test_output"].strip().splitlines()[-1] if result["test_output"].strip() else ""
            emit_event("VERIFIER", f"pytest: {last_line}  ✓", run_id)
        else:
            emit_event("VERIFIER", f"✗ tests failed (attempt {retry_count + 1})", run_id)
        return result

    def _run_on_nosana(self, repo_path: str, run_id: str) -> dict | None:
        try:
            headers = {"Authorization": f"Bearer {settings.nosana_api_key}"}
            payload = {
                "image": "python:3.11-slim",
                "cmd": ["sh", "-c", "pip install -e . -q && pytest --tb=short -q"],
                "workspace": repo_path,
                "timeout": 90,
            }
            resp = httpx.post(
                f"{settings.nosana_base_url}/jobs",
                json=payload,
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            job_id = resp.json()["job_id"]

            for _ in range(30):
                time.sleep(3)
                status_resp = httpx.get(
                    f"{settings.nosana_base_url}/jobs/{job_id}",
                    headers=headers,
                    timeout=10,
                )
                data = status_resp.json()
                if data.get("status") == "completed":
                    output = data.get("stdout", "")
                    passed = data.get("exit_code", 1) == 0
                    return {"passed": passed, "test_output": output}
            return None
        except Exception:
            return None
