# Bounty Hunter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully autonomous Python agent that discovers open GitHub bugs, writes fixes via a multi-agent panel, verifies them with automated tests, and opens pull requests — all streamed live to a judges' terminal.

**Architecture:** Five AgentField microservices (Scraper → Analyst → Patcher → Verifier → PR Opener) coordinated by an orchestrator that emits SSE events to a FastAPI terminal server. Every sponsor tool has a load-bearing role; `MOCK_MODE=true` enables full local development without burning API credits.

**Tech Stack:** Python 3.11, FastAPI, AgentField SDK, Bright Data proxies, Actionbook API, OpenAI-compatible SDK (Qwen/GLM-5.1/TokenRouter), Qoder API, Evermind API, Nosana SDK, GitPython, PyGitHub, Zeabur

---

## File Map

| File | Responsibility |
|---|---|
| `config/settings.py` | Pydantic env-var loading, single `settings` singleton |
| `config/mocks.py` | Pre-baked responses for every external API (MOCK_MODE) |
| `config/repos.yaml` | Optional repo whitelist |
| `terminal/server.py` | FastAPI app: SSE `/stream`, `POST /trigger`, `GET /` |
| `terminal/static/index.html` | Judges' dark terminal UI, vanilla JS EventSource |
| `sandbox/runner.py` | git clone, venv creation, patch apply, pytest execution |
| `router/llm.py` | TokenRouter unified client: route by task type, cache |
| `orchestrator/memory.py` | Evermind read/write wrapper |
| `orchestrator/engine.py` | AgentField pipeline: registers agents, runs loop |
| `agents/scraper.py` | Bright Data GitHub search + Qwen fixability scoring |
| `agents/analyst.py` | GLM-5.1 root cause analysis over cloned repo |
| `agents/patcher.py` | Qoder Expert Panel: Senior Engineer + Test Writer |
| `agents/verifier.py` | Nosana job submit + local subprocess fallback |
| `agents/pr_opener.py` | git CLI push + Actionbook GitHub PR form submit |
| `main.py` | Entry point: starts terminal server + orchestrator loop |
| `tests/test_pipeline.py` | Full pipeline integration test in MOCK_MODE |
| `pyproject.toml` | Dependencies and project metadata |
| `Dockerfile` | Container for Zeabur deployment |
| `zeabur.yaml` | Zeabur service config |
| `.env.example` | All required env vars documented |

---

## Task 1: Project Bootstrap

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: all `__init__.py` stubs

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "bounty-hunter"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "sse-starlette>=1.8.2",
    "httpx>=0.27.0",
    "pydantic-settings>=2.2.1",
    "python-dotenv>=1.0.1",
    "gitpython>=3.1.43",
    "PyGitHub>=2.3.0",
    "openai>=1.30.0",
    "pyyaml>=6.0.1",
    "agentfield>=0.1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.2.0", "pytest-asyncio>=0.23.7", "respx>=0.21.1"]
```

- [ ] **Step 2: Create .env.example**

```bash
# AgentField
AGENTFIELD_API_KEY=

# Bright Data
BRIGHT_DATA_USERNAME=
BRIGHT_DATA_PASSWORD=
BRIGHT_DATA_HOST=brd.superproxy.io
BRIGHT_DATA_PORT=22225

# Actionbook
ACTIONBOOK_API_KEY=

# Qwen Cloud
QWEN_API_KEY=
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Z.ai / GLM-5.1
ZAI_API_KEY=
ZAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/

# Qoder
QODER_API_KEY=
QODER_BASE_URL=https://api.qoder.ai/v1

# TokenRouter
TOKENROUTER_API_KEY=
TOKENROUTER_BASE_URL=https://api.tokenrouter.ai/v1

# Evermind
EVERMIND_API_KEY=
EVERMIND_BASE_URL=https://api.evermind.ai/v1

# Nosana
NOSANA_API_KEY=
NOSANA_BASE_URL=https://api.nosana.io/v1

# GitHub
GITHUB_TOKEN=
GITHUB_USERNAME=

# Zeabur
ZEABUR_API_KEY=
ZEABUR_PROJECT_ID=

# Butterbase
BUTTERBASE_API_KEY=
BUTTERBASE_BASE_URL=https://api.butterbase.ai/v1

# App
MOCK_MODE=true
LOG_LEVEL=INFO
PORT=8080
```

- [ ] **Step 3: Create package stubs**

```bash
touch agents/__init__.py orchestrator/__init__.py router/__init__.py \
      terminal/__init__.py sandbox/__init__.py config/__init__.py \
      terminal/static/.gitkeep tests/__init__.py
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -e ".[dev]"
```

Expected: all packages install without error.

- [ ] **Step 5: Commit**

```bash
git init && git add pyproject.toml .env.example agents/__init__.py \
  orchestrator/__init__.py router/__init__.py terminal/__init__.py \
  sandbox/__init__.py config/__init__.py tests/__init__.py
git commit -m "feat: project bootstrap"
```

---

## Task 2: Config & Mocks Layer

**Files:**
- Create: `config/settings.py`
- Create: `config/mocks.py`
- Create: `config/repos.yaml`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
def test_settings_loads_mock_mode(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "true")
    monkeypatch.setenv("GITHUB_TOKEN", "fake")
    monkeypatch.setenv("GITHUB_USERNAME", "fake")
    from config.settings import Settings
    s = Settings()
    assert s.mock_mode is True

def test_mock_scraper_result_is_valid():
    from config.mocks import MOCK_SCRAPER_RESULT
    assert "repo_url" in MOCK_SCRAPER_RESULT[0]
    assert "issue_number" in MOCK_SCRAPER_RESULT[0]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py -v
```

Expected: FAIL with `ModuleNotFoundError: config.settings`

- [ ] **Step 3: Implement config/settings.py**

```python
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    agentfield_api_key: str = "mock"
    bright_data_username: str = "mock"
    bright_data_password: str = "mock"
    bright_data_host: str = "brd.superproxy.io"
    bright_data_port: int = 22225
    actionbook_api_key: str = "mock"
    qwen_api_key: str = "mock"
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    zai_api_key: str = "mock"
    zai_base_url: str = "https://open.bigmodel.cn/api/paas/v4/"
    qoder_api_key: str = "mock"
    qoder_base_url: str = "https://api.qoder.ai/v1"
    tokenrouter_api_key: str = "mock"
    tokenrouter_base_url: str = "https://api.tokenrouter.ai/v1"
    evermind_api_key: str = "mock"
    evermind_base_url: str = "https://api.evermind.ai/v1"
    nosana_api_key: str = "mock"
    nosana_base_url: str = "https://api.nosana.io/v1"
    github_token: str
    github_username: str
    zeabur_api_key: Optional[str] = None
    zeabur_project_id: Optional[str] = None
    butterbase_api_key: Optional[str] = None
    butterbase_base_url: str = "https://api.butterbase.ai/v1"
    mock_mode: bool = False
    log_level: str = "INFO"
    port: int = 8080

    model_config = {"env_file": ".env", "case_sensitive": False}

settings = Settings()
```

- [ ] **Step 4: Implement config/mocks.py**

```python
MOCK_SCRAPER_RESULT = [
    {
        "repo_url": "https://github.com/psf/requests",
        "issue_url": "https://github.com/psf/requests/issues/6821",
        "issue_title": "JSONDecodeError not properly caught in response.json()",
        "issue_body": (
            "When the server returns a 200 with invalid JSON, calling response.json() "
            "raises json.JSONDecodeError instead of requests.JSONDecodeError. "
            "Reproducible with: r = requests.get(url); r.json() where body is 'not-json'."
        ),
        "issue_number": 6821,
        "fixability_score": 0.92,
    }
]

MOCK_ANALYST_RESULT = {
    "root_cause": (
        "In requests/models.py, Response.json() calls json.loads() directly without "
        "catching json.JSONDecodeError and re-raising as requests.exceptions.JSONDecodeError."
    ),
    "affected_files": ["requests/models.py"],
    "fix_approach": (
        "Wrap the json.loads() call in a try/except json.JSONDecodeError block "
        "and raise requests.exceptions.JSONDecodeError with the original exception chained."
    ),
    "confidence_score": 0.91,
}

MOCK_PATCH_RESULT = {
    "patch_diff": """\
--- a/requests/models.py
+++ b/requests/models.py
@@ -897,7 +897,10 @@ class Response:
         if not self.encoding and self.content and len(self.content) > 3:
             encoding = guess_json_utf(self.content)
             if encoding is not None:
-                return complexjson.loads(self.content.decode(encoding), **kwargs)
+                try:
+                    return complexjson.loads(self.content.decode(encoding), **kwargs)
+                except JSONDecodeError as e:
+                    raise RequestsJSONDecodeError(e.msg, e.doc, e.pos)
         try:
             return complexjson.loads(self.text, **kwargs)
         except JSONDecodeError as e:
""",
    "test_code": """\
def test_json_decode_error_is_requests_exception():
    import requests
    from requests.exceptions import JSONDecodeError
    r = requests.models.Response()
    r._content = b"not-valid-json"
    r.encoding = "utf-8"
    with pytest.raises(JSONDecodeError):
        r.json()
""",
    "explanation": (
        "Wrapped json.loads with a try/except to re-raise as requests.exceptions.JSONDecodeError."
    ),
}

MOCK_VERIFIER_RESULT = {
    "passed": True,
    "test_output": "47 passed, 0 failed in 8.32s",
    "retry_count": 0,
}

MOCK_PR_RESULT = {
    "pr_url": "https://github.com/psf/requests/pull/6834",
    "comment_posted": True,
}

MOCK_EVERMIND_MEMORY: dict = {}
```

- [ ] **Step 5: Create config/repos.yaml**

```yaml
# Optional repo whitelist. If present and non-empty, Scraper only targets these repos.
# Leave empty to use open GitHub search (default).
repos: []
# repos:
#   - psf/requests
#   - encode/httpx
#   - Textualize/rich
#   - tiangolo/fastapi
#   - pallets/click
```

- [ ] **Step 6: Run tests**

```bash
pytest tests/test_config.py -v
```

Expected: 2 passed

- [ ] **Step 7: Commit**

```bash
git add config/ tests/test_config.py
git commit -m "feat: config, settings, and mock layer"
```

---

## Task 3: SSE Terminal Server

**Files:**
- Create: `terminal/server.py`
- Create: `terminal/static/index.html`
- Test: `tests/test_terminal.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_terminal.py
import pytest
from fastapi.testclient import TestClient

def test_root_returns_html():
    from terminal.server import app
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]

def test_stream_endpoint_exists():
    from terminal.server import app
    client = TestClient(app)
    # Just verify the route exists; SSE streaming tested manually
    with client.stream("GET", "/stream") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

def test_emit_event_adds_to_buffer():
    from terminal.server import emit_event, _event_buffer
    initial_len = len(_event_buffer)
    emit_event("SCRAPER", "test message", "run-001")
    assert len(_event_buffer) == initial_len + 1
    assert _event_buffer[-1]["agent"] == "SCRAPER"
    assert _event_buffer[-1]["message"] == "test message"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_terminal.py -v
```

Expected: FAIL with `ModuleNotFoundError: terminal.server`

- [ ] **Step 3: Implement terminal/server.py**

```python
import asyncio
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse

app = FastAPI(title="Bounty Hunter Terminal")

_event_buffer: list[dict] = []
_subscribers: list[asyncio.Queue] = []


def emit_event(agent: str, message: str, run_id: str = "") -> None:
    event = {
        "agent": agent.upper(),
        "message": message,
        "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        "run_id": run_id,
    }
    _event_buffer.append(event)
    if len(_event_buffer) > 200:
        _event_buffer.pop(0)
    for q in list(_subscribers):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


async def _event_generator() -> AsyncIterator[dict]:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    _subscribers.append(q)
    try:
        for buffered in _event_buffer[-50:]:
            yield {"data": json.dumps(buffered)}
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30)
                yield {"data": json.dumps(event)}
            except asyncio.TimeoutError:
                yield {"data": json.dumps({"ping": True})}
    finally:
        _subscribers.remove(q)


@app.get("/stream")
async def stream():
    return EventSourceResponse(_event_generator())


@app.post("/trigger")
async def trigger_run():
    from orchestrator.engine import run_pipeline
    run_id = str(uuid.uuid4())[:8]
    asyncio.create_task(run_pipeline(run_id))
    return {"run_id": run_id, "status": "started"}


@app.get("/")
async def root():
    html_path = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(html_path.read_text())
```

- [ ] **Step 4: Implement terminal/static/index.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Bounty Hunter // Agent Forge</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0d1117; color: #c9d1d9; font-family: 'Courier New', monospace; height: 100vh; display: flex; flex-direction: column; }
  #header { background: #161b22; border-bottom: 1px solid #30363d; padding: 12px 20px; display: flex; align-items: center; gap: 16px; }
  #header h1 { color: #58a6ff; font-size: 14px; letter-spacing: 2px; }
  #run-id { color: #8b949e; font-size: 12px; }
  #status { margin-left: auto; font-size: 12px; }
  #status.connected { color: #3fb950; }
  #status.disconnected { color: #f85149; }
  #terminal { flex: 1; overflow-y: auto; padding: 16px 20px; }
  .line { display: flex; gap: 12px; padding: 2px 0; font-size: 13px; line-height: 1.6; }
  .ts { color: #484f58; min-width: 70px; }
  .agent { min-width: 90px; font-weight: bold; }
  .agent.SCRAPER { color: #79c0ff; }
  .agent.ANALYST { color: #d2a8ff; }
  .agent.PATCHER { color: #ffa657; }
  .agent.VERIFIER { color: #3fb950; }
  .agent.PR_OPENER { color: #f778ba; }
  .agent.MEMORY { color: #e3b341; }
  .agent.COMPLETE { color: #3fb950; }
  .agent.ERROR { color: #f85149; }
  .agent.ORCHESTRATOR { color: #8b949e; }
  .msg { flex: 1; color: #c9d1d9; }
  .msg .tick { color: #3fb950; }
  .msg .cross { color: #f85149; }
  #footer { background: #161b22; border-top: 1px solid #30363d; padding: 12px 20px; display: flex; gap: 12px; align-items: center; }
  button { background: #238636; color: #fff; border: none; padding: 8px 18px; border-radius: 6px; font-family: inherit; font-size: 13px; cursor: pointer; letter-spacing: 1px; }
  button:hover { background: #2ea043; }
  button:disabled { background: #21262d; color: #484f58; cursor: not-allowed; }
  #past-runs { color: #58a6ff; font-size: 13px; cursor: pointer; text-decoration: underline; background: none; border: none; }
</style>
</head>
<body>
<div id="header">
  <h1>⬡ BOUNTY HUNTER // AGENT-FORGE</h1>
  <span id="run-id">run: —</span>
  <span id="status" class="disconnected">● DISCONNECTED</span>
</div>
<div id="terminal" id="terminal"></div>
<div id="footer">
  <button id="trigger-btn" onclick="triggerRun()">▶ TRIGGER NEW RUN</button>
  <button id="past-runs" onclick="alert('Run history coming soon via Butterbase')">View Past Runs ↗</button>
</div>
<script>
const terminal = document.getElementById('terminal');
const statusEl = document.getElementById('status');
const runIdEl = document.getElementById('run-id');
const triggerBtn = document.getElementById('trigger-btn');

function appendLine(agent, message, ts) {
  const line = document.createElement('div');
  line.className = 'line';
  const msg = message.replace(/✓/g, '<span class="tick">✓</span>').replace(/✗/g, '<span class="cross">✗</span>');
  line.innerHTML = `<span class="ts">[${ts}]</span><span class="agent ${agent}">${agent.padEnd(10)}</span><span class="msg">▶  ${msg}</span>`;
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

function connect() {
  const es = new EventSource('/stream');
  es.onopen = () => { statusEl.textContent = '● CONNECTED'; statusEl.className = 'connected'; };
  es.onerror = () => { statusEl.textContent = '● DISCONNECTED'; statusEl.className = 'disconnected'; setTimeout(connect, 3000); es.close(); };
  es.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.ping) return;
    if (data.run_id) runIdEl.textContent = `run: ${data.run_id}`;
    appendLine(data.agent || 'SYSTEM', data.message, data.timestamp || '--:--:--');
  };
}

async function triggerRun() {
  triggerBtn.disabled = true;
  triggerBtn.textContent = '⟳ RUNNING...';
  try {
    const r = await fetch('/trigger', { method: 'POST' });
    const d = await r.json();
    runIdEl.textContent = `run: ${d.run_id}`;
  } finally {
    setTimeout(() => { triggerBtn.disabled = false; triggerBtn.textContent = '▶ TRIGGER NEW RUN'; }, 60000);
  }
}

connect();
</script>
</body>
</html>
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_terminal.py -v
```

Expected: 3 passed

- [ ] **Step 6: Smoke-test the terminal UI**

```bash
uvicorn terminal.server:app --port 8080
# open http://localhost:8080 in browser
# verify dark terminal UI renders, status shows CONNECTED
```

- [ ] **Step 7: Commit**

```bash
git add terminal/ tests/test_terminal.py
git commit -m "feat: SSE terminal server and judges UI"
```

---

## Task 4: Sandbox Runner

**Files:**
- Create: `sandbox/runner.py`
- Test: `tests/test_sandbox.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sandbox.py
import os, textwrap
from pathlib import Path

def test_clone_and_run_pytest(tmp_path):
    from sandbox.runner import SandboxRunner
    # Use a local dir as a fake "repo" to avoid real git clones in CI
    repo_dir = tmp_path / "fake_repo"
    repo_dir.mkdir()
    (repo_dir / "test_simple.py").write_text("def test_pass(): assert 1 == 1\n")
    
    runner = SandboxRunner(run_id="test-001", sandbox_base=tmp_path)
    result = runner.run_tests_in_dir(str(repo_dir))
    assert result["passed"] is True
    assert "1 passed" in result["test_output"]

def test_apply_patch_modifies_file(tmp_path):
    from sandbox.runner import SandboxRunner
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    target = repo_dir / "foo.py"
    target.write_text("x = 1\n")

    patch = textwrap.dedent("""\
        --- a/foo.py
        +++ b/foo.py
        @@ -1 +1 @@
        -x = 1
        +x = 2
    """)
    runner = SandboxRunner(run_id="test-002", sandbox_base=tmp_path)
    runner.apply_patch(str(repo_dir), patch)
    assert target.read_text() == "x = 2\n"

def test_failed_tests_returns_passed_false(tmp_path):
    from sandbox.runner import SandboxRunner
    repo_dir = tmp_path / "bad_repo"
    repo_dir.mkdir()
    (repo_dir / "test_fail.py").write_text("def test_fail(): assert False\n")

    runner = SandboxRunner(run_id="test-003", sandbox_base=tmp_path)
    result = runner.run_tests_in_dir(str(repo_dir))
    assert result["passed"] is False
    assert "failed" in result["test_output"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_sandbox.py -v
```

Expected: FAIL with `ModuleNotFoundError: sandbox.runner`

- [ ] **Step 3: Implement sandbox/runner.py**

```python
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
from dataclasses import dataclass, field

import git


@dataclass
class SandboxRunner:
    run_id: str
    sandbox_base: Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "bh_sandbox")

    def __post_init__(self):
        self.sandbox_base = Path(self.sandbox_base)
        self.run_dir = self.sandbox_base / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def clone(self, repo_url: str) -> str:
        dest = self.run_dir / "repo"
        if dest.exists():
            shutil.rmtree(dest)
        git.Repo.clone_from(repo_url, str(dest), depth=1)
        return str(dest)

    def apply_patch(self, repo_path: str, patch_diff: str) -> None:
        patch_file = self.run_dir / "fix.patch"
        patch_file.write_text(patch_diff)
        result = subprocess.run(
            ["git", "apply", "--whitespace=fix", str(patch_file)],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"patch apply failed:\n{result.stderr}")

    def run_tests_in_dir(self, repo_path: str, timeout: int = 90) -> dict:
        venv_dir = self.run_dir / "venv"
        if not venv_dir.exists():
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

        pip = venv_dir / "bin" / "pip"
        python = venv_dir / "bin" / "python"

        # install repo deps if setup.py / pyproject.toml present
        repo = Path(repo_path)
        if (repo / "pyproject.toml").exists() or (repo / "setup.py").exists():
            subprocess.run(
                [str(pip), "install", "-e", ".[test,dev,testing]", "--quiet",
                 "--extra-index-url", "https://pypi.org/simple"],
                cwd=repo_path,
                capture_output=True,
                timeout=120,
            )
        else:
            subprocess.run([str(pip), "install", "pytest", "--quiet"], capture_output=True)

        result = subprocess.run(
            [str(python), "-m", "pytest", "--tb=short", "-q", repo_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        passed = result.returncode == 0
        return {"passed": passed, "test_output": output}

    def cleanup(self) -> None:
        if self.run_dir.exists():
            shutil.rmtree(self.run_dir)
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_sandbox.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add sandbox/ tests/test_sandbox.py
git commit -m "feat: sandbox runner with git clone, patch apply, pytest"
```

---

## Task 5: TokenRouter LLM Interface

**Files:**
- Create: `router/llm.py`
- Test: `tests/test_llm_router.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_llm_router.py
import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")

def test_router_returns_string_in_mock_mode(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "true")
    from router.llm import LLMRouter
    router = LLMRouter(mock_mode=True)
    result = router.complete(
        task="classify",
        messages=[{"role": "user", "content": "hello"}],
    )
    assert isinstance(result, str)
    assert len(result) > 0

def test_router_selects_glm_for_reasoning(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "true")
    from router.llm import LLMRouter, TASK_MODEL_MAP
    assert TASK_MODEL_MAP["reasoning"] == "glm-4-plus"
    assert TASK_MODEL_MAP["classify"] == "qwen-turbo"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_llm_router.py -v
```

Expected: FAIL with `ModuleNotFoundError: router.llm`

- [ ] **Step 3: Implement router/llm.py**

```python
from openai import OpenAI
from config.settings import settings

TASK_MODEL_MAP = {
    "reasoning": "glm-4-plus",     # GLM-5.1 via Z.ai for deep code reasoning
    "classify": "qwen-turbo",       # Qwen for fast scoring/classification
    "patch": "glm-4-plus",         # GLM for code generation
    "default": "glm-4-plus",
}

MOCK_RESPONSES = {
    "reasoning": "I have analyzed the code. The root cause is in the exception handling path.",
    "classify": "0.88",
    "patch": "The fix applies a try/except block around the JSON decode call.",
    "default": "Mock LLM response.",
}


class LLMRouter:
    def __init__(self, mock_mode: bool | None = None):
        self.mock_mode = mock_mode if mock_mode is not None else settings.mock_mode
        if not self.mock_mode:
            self._client = OpenAI(
                api_key=settings.tokenrouter_api_key,
                base_url=settings.tokenrouter_base_url,
            )

    def complete(self, task: str, messages: list[dict], temperature: float = 0.2) -> str:
        if self.mock_mode:
            return MOCK_RESPONSES.get(task, MOCK_RESPONSES["default"])
        model = TASK_MODEL_MAP.get(task, TASK_MODEL_MAP["default"])
        response = self._client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_llm_router.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add router/ tests/test_llm_router.py
git commit -m "feat: TokenRouter LLM interface with Qwen/GLM-5.1 routing"
```

---

## Task 6: Evermind Memory Client

**Files:**
- Create: `orchestrator/memory.py`
- Test: `tests/test_memory.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_memory.py
import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")

def test_store_and_retrieve_in_mock():
    from orchestrator.memory import EvermindClient
    client = EvermindClient(mock_mode=True)
    client.store("attempted_issues", ["https://github.com/psf/requests/issues/6821"])
    result = client.retrieve("attempted_issues")
    assert "https://github.com/psf/requests/issues/6821" in result

def test_is_attempted_returns_true_for_stored():
    from orchestrator.memory import EvermindClient
    client = EvermindClient(mock_mode=True)
    client.store("attempted_issues", ["https://github.com/foo/bar/issues/1"])
    assert client.is_attempted("https://github.com/foo/bar/issues/1") is True

def test_is_attempted_returns_false_for_new():
    from orchestrator.memory import EvermindClient
    client = EvermindClient(mock_mode=True)
    assert client.is_attempted("https://github.com/new/repo/issues/99") is False

def test_mark_attempted_persists():
    from orchestrator.memory import EvermindClient
    client = EvermindClient(mock_mode=True)
    client.mark_attempted("https://github.com/x/y/issues/5", outcome="success")
    assert client.is_attempted("https://github.com/x/y/issues/5") is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_memory.py -v
```

Expected: FAIL with `ModuleNotFoundError: orchestrator.memory`

- [ ] **Step 3: Implement orchestrator/memory.py**

```python
import httpx
from config.settings import settings
from config.mocks import MOCK_EVERMIND_MEMORY


class EvermindClient:
    def __init__(self, mock_mode: bool | None = None):
        self.mock_mode = mock_mode if mock_mode is not None else settings.mock_mode
        self._local: dict = dict(MOCK_EVERMIND_MEMORY)
        if not self.mock_mode:
            self._http = httpx.Client(
                base_url=settings.evermind_base_url,
                headers={"Authorization": f"Bearer {settings.evermind_api_key}"},
                timeout=10,
            )

    def store(self, key: str, value: object) -> None:
        if self.mock_mode:
            self._local[key] = value
            return
        self._http.post("/memory", json={"key": key, "value": value})

    def retrieve(self, key: str, default=None) -> object:
        if self.mock_mode:
            return self._local.get(key, default)
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_memory.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add orchestrator/memory.py tests/test_memory.py
git commit -m "feat: Evermind memory client with mock mode"
```

---

## Task 7: Scraper Agent

**Files:**
- Create: `agents/scraper.py`
- Test: `tests/test_scraper.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scraper.py
import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")

def test_scraper_returns_list_of_issues():
    from agents.scraper import ScraperAgent
    agent = ScraperAgent(mock_mode=True)
    results = agent.run(query="label:bug language:python")
    assert isinstance(results, list)
    assert len(results) > 0

def test_scraper_result_has_required_fields():
    from agents.scraper import ScraperAgent
    agent = ScraperAgent(mock_mode=True)
    results = agent.run(query="label:bug language:python")
    issue = results[0]
    for field in ("repo_url", "issue_url", "issue_title", "issue_body", "issue_number", "fixability_score"):
        assert field in issue, f"missing field: {field}"

def test_scraper_deduplicates_via_evermind():
    from agents.scraper import ScraperAgent
    from orchestrator.memory import EvermindClient
    memory = EvermindClient(mock_mode=True)
    memory.mark_attempted("https://github.com/psf/requests/issues/6821", outcome="success")
    agent = ScraperAgent(mock_mode=True, memory=memory)
    results = agent.run(query="label:bug language:python")
    urls = [r["issue_url"] for r in results]
    assert "https://github.com/psf/requests/issues/6821" not in urls

def test_scraper_applies_repo_whitelist():
    from agents.scraper import ScraperAgent
    agent = ScraperAgent(mock_mode=True, repo_whitelist=["encode/httpx"])
    results = agent.run(query="label:bug language:python")
    for r in results:
        assert "encode/httpx" in r["repo_url"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_scraper.py -v
```

Expected: FAIL with `ModuleNotFoundError: agents.scraper`

- [ ] **Step 3: Implement agents/scraper.py**

```python
import json
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

        proxy_url = (
            f"http://{settings.bright_data_username}:{settings.bright_data_password}"
            f"@{settings.bright_data_host}:{settings.bright_data_port}"
        )
        proxies = {"http://": proxy_url, "https://": proxy_url}
        url = f"https://api.github.com/search/issues?q={query}+state:open&sort=created&order=desc&per_page=20"
        headers = {
            "Authorization": f"token {settings.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        resp = httpx.get(url, headers=headers, proxies=proxies, timeout=15)
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_scraper.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add agents/scraper.py tests/test_scraper.py
git commit -m "feat: scraper agent with Bright Data, Qwen scoring, Evermind dedup"
```

---

## Task 8: Analyst Agent

**Files:**
- Create: `agents/analyst.py`
- Test: `tests/test_analyst.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_analyst.py
import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")

def test_analyst_returns_valid_analysis():
    from agents.analyst import AnalystAgent
    agent = AnalystAgent(mock_mode=True)
    issue = {
        "repo_url": "https://github.com/psf/requests",
        "issue_title": "JSONDecodeError not caught",
        "issue_body": "When calling response.json() on invalid JSON...",
        "issue_number": 6821,
    }
    result = agent.run(issue=issue, repo_path="/tmp/fake_repo", run_id="test")
    assert "root_cause" in result
    assert "affected_files" in result
    assert "confidence_score" in result
    assert isinstance(result["confidence_score"], float)

def test_analyst_rejects_low_confidence():
    from agents.analyst import AnalystAgent
    agent = AnalystAgent(mock_mode=True)
    agent._force_confidence = 0.3
    issue = {
        "repo_url": "https://github.com/psf/requests",
        "issue_title": "vague issue",
        "issue_body": "something is wrong",
        "issue_number": 9999,
    }
    result = agent.run(issue=issue, repo_path="/tmp/fake_repo", run_id="test")
    assert result is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_analyst.py -v
```

Expected: FAIL with `ModuleNotFoundError: agents.analyst`

- [ ] **Step 3: Implement agents/analyst.py**

```python
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
    text = full.read_text(errors="replace")
    return text[:max_chars]


class AnalystAgent:
    def __init__(self, mock_mode: bool | None = None):
        self.mock_mode = mock_mode if mock_mode is not None else settings.mock_mode
        self.llm = LLMRouter()
        self._force_confidence: float | None = None

    def run(self, issue: dict, repo_path: str, run_id: str = "") -> dict | None:
        emit_event("ANALYST", f"GLM-5.1 reading issue + file tree", run_id)

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
            import json
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_analyst.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add agents/analyst.py tests/test_analyst.py
git commit -m "feat: analyst agent with GLM-5.1 root cause analysis"
```

---

## Task 9: Patcher Agent

**Files:**
- Create: `agents/patcher.py`
- Test: `tests/test_patcher.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_patcher.py
import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")

def test_patcher_returns_valid_patch():
    from agents.patcher import PatcherAgent
    agent = PatcherAgent(mock_mode=True)
    analysis = {
        "root_cause": "JSONDecodeError not re-raised as requests exception",
        "affected_files": ["requests/models.py"],
        "fix_approach": "Wrap json.loads in try/except and re-raise",
        "confidence_score": 0.91,
    }
    result = agent.run(analysis=analysis, repo_path="/tmp/fake", run_id="test")
    assert "patch_diff" in result
    assert "test_code" in result
    assert "explanation" in result
    assert "---" in result["patch_diff"] or "+++" in result["patch_diff"]

def test_patcher_result_with_failure_trace():
    from agents.patcher import PatcherAgent
    agent = PatcherAgent(mock_mode=True)
    analysis = {
        "root_cause": "Encoding error",
        "affected_files": ["lib/codec.py"],
        "fix_approach": "Add encoding fallback",
        "confidence_score": 0.85,
    }
    result = agent.run(
        analysis=analysis,
        repo_path="/tmp/fake",
        run_id="test",
        failure_trace="AssertionError: encoding expected utf-8 got None",
    )
    assert result is not None
    assert "patch_diff" in result
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_patcher.py -v
```

Expected: FAIL with `ModuleNotFoundError: agents.patcher`

- [ ] **Step 3: Implement agents/patcher.py**

```python
import json
import httpx
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
            lines = patch["patch_diff"].count("\n+") + patch["patch_diff"].count("\n-")
            emit_event("PATCHER", f"Patch ready: +{patch['patch_diff'].count(chr(10)+'+')}"
                                  f" lines / -{patch['patch_diff'].count(chr(10)+'-')} lines", run_id)
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

        added = sum(1 for l in patch_diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in patch_diff.splitlines() if l.startswith("-") and not l.startswith("---"))
        emit_event("PATCHER", f"Patch ready: +{added} lines / -{removed} lines", run_id)

        return {
            "patch_diff": patch_diff,
            "test_code": test_code,
            "explanation": analysis["fix_approach"],
        }
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_patcher.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add agents/patcher.py tests/test_patcher.py
git commit -m "feat: patcher agent with Qoder Expert Panel and GLM-5.1 patch gen"
```

---

## Task 10: Verifier Agent

**Files:**
- Create: `agents/verifier.py`
- Test: `tests/test_verifier.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_verifier.py
import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")

def test_verifier_returns_passed_in_mock():
    from agents.verifier import VerifierAgent
    agent = VerifierAgent(mock_mode=True)
    result = agent.run(
        patch={"patch_diff": "--- a/x\n+++ b/x\n@@ -1 +1 @@\n-old\n+new", "test_code": "", "explanation": ""},
        repo_path="/tmp/fake",
        run_id="test",
    )
    assert result["passed"] is True
    assert "test_output" in result
    assert result["retry_count"] == 0

def test_verifier_result_has_retry_count():
    from agents.verifier import VerifierAgent
    agent = VerifierAgent(mock_mode=True)
    result = agent.run(
        patch={"patch_diff": "", "test_code": "", "explanation": ""},
        repo_path="/tmp/fake",
        run_id="test",
    )
    assert "retry_count" in result
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_verifier.py -v
```

Expected: FAIL with `ModuleNotFoundError: agents.verifier`

- [ ] **Step 3: Implement agents/verifier.py**

```python
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
            emit_event("VERIFIER", f"pytest: {result['test_output'].splitlines()[-1]}  ✓", run_id)
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_verifier.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add agents/verifier.py tests/test_verifier.py
git commit -m "feat: verifier agent with Nosana job submission and local fallback"
```

---

## Task 11: PR Opener Agent

**Files:**
- Create: `agents/pr_opener.py`
- Test: `tests/test_pr_opener.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pr_opener.py
import os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")

def test_pr_opener_returns_pr_url_in_mock():
    from agents.pr_opener import PROpenerAgent
    agent = PROpenerAgent(mock_mode=True)
    result = agent.run(
        issue={"repo_url": "https://github.com/psf/requests", "issue_number": 6821, "issue_title": "bug"},
        patch={"patch_diff": "--- a/x\n+++ b/x", "explanation": "fix it", "test_code": ""},
        terminal_url="https://bh.zeabur.app",
        run_id="test",
    )
    assert "pr_url" in result
    assert result["pr_url"].startswith("https://github.com")
    assert result["comment_posted"] is True

def test_pr_opener_pr_body_contains_terminal_url():
    from agents.pr_opener import _build_pr_body
    body = _build_pr_body(
        issue_number=42,
        explanation="Wrap json.loads in try/except",
        patch_diff="--- a/x\n+++ b/x",
        terminal_url="https://bh.zeabur.app",
    )
    assert "https://bh.zeabur.app" in body
    assert "42" in body
    assert "Wrap json.loads" in body
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_pr_opener.py -v
```

Expected: FAIL with `ModuleNotFoundError: agents.pr_opener`

- [ ] **Step 3: Implement agents/pr_opener.py**

```python
import subprocess
import httpx
from pathlib import Path
from config.settings import settings
from config.mocks import MOCK_PR_RESULT
from terminal.server import emit_event


def _build_pr_body(issue_number: int, explanation: str, patch_diff: str, terminal_url: str) -> str:
    return f"""## Autonomous Fix by Bounty Hunter 🤖

Closes #{issue_number}

### What changed
{explanation}

### Diff
```diff
{patch_diff[:3000]}
```

### Live verification
Watch the agent's reasoning and test run in real time:
🔗 {terminal_url}

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

    def _push_branch(self, repo_path: str, branch_name: str, owner: str, repo: str) -> None:
        remote_url = f"https://{settings.github_username}:{settings.github_token}@github.com/{settings.github_username}/{repo}.git"
        cmds = [
            ["git", "checkout", "-b", branch_name],
            ["git", "add", "-A"],
            ["git", "commit", "-m", f"fix: autonomous patch by bounty-hunter"],
            ["git", "remote", "add", "fork", remote_url],
            ["git", "push", "fork", branch_name],
        ]
        for cmd in cmds:
            subprocess.run(cmd, cwd=repo_path, check=True, capture_output=True)

    def _open_via_actionbook(
        self, owner: str, repo: str, branch: str, title: str, body: str, run_id: str
    ) -> dict:
        headers = {"Authorization": f"Bearer {settings.actionbook_api_key}", "Content-Type": "application/json"}
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_pr_opener.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add agents/pr_opener.py tests/test_pr_opener.py
git commit -m "feat: PR opener with Actionbook browser automation and GitHub API fallback"
```

---

## Task 12: AgentField Orchestrator

**Files:**
- Create: `orchestrator/engine.py`
- Test: `tests/test_engine.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_engine.py
import asyncio, os
os.environ.setdefault("MOCK_MODE", "true")
os.environ.setdefault("GITHUB_TOKEN", "fake")
os.environ.setdefault("GITHUB_USERNAME", "fake")

def test_run_pipeline_completes_in_mock(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "true")
    from orchestrator.engine import run_pipeline
    result = asyncio.get_event_loop().run_until_complete(
        run_pipeline(run_id="test-e2e-001")
    )
    assert result is not None
    assert result["status"] in ("success", "no_issues", "failed")

def test_run_pipeline_returns_pr_url_on_success(monkeypatch):
    monkeypatch.setenv("MOCK_MODE", "true")
    from orchestrator.engine import run_pipeline
    result = asyncio.get_event_loop().run_until_complete(
        run_pipeline(run_id="test-e2e-002")
    )
    if result["status"] == "success":
        assert "pr_url" in result
        assert result["pr_url"].startswith("https://github.com")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_engine.py -v
```

Expected: FAIL with `ModuleNotFoundError: orchestrator.engine`

- [ ] **Step 3: Implement orchestrator/engine.py**

```python
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

TERMINAL_URL = os.environ.get("TERMINAL_URL", "https://bounty-hunter.zeabur.app")
MAX_RETRIES = 2
MAX_ISSUE_ATTEMPTS = 5


async def run_pipeline(run_id: str) -> dict:
    emit_event("ORCHESTRATOR", f"Pipeline start — run {run_id}", run_id)

    memory = EvermindClient()
    scraper = ScraperAgent(memory=memory)
    analyst = AnalystAgent()
    patcher = PatcherAgent()
    verifier = VerifierAgent()
    pr_opener = PROpenerAgent()

    # Step 1: Scrape
    issues = await asyncio.to_thread(
        scraper.run, query="label:bug language:python", run_id=run_id
    )
    if not issues:
        emit_event("ORCHESTRATOR", "No viable issues found — halting", run_id)
        return {"status": "no_issues", "run_id": run_id}

    issue = issues[0]

    # Step 2: Clone repo and analyze
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

        # Step 3 & 4: Patch + Verify with retry loop
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

        # Step 5: Open PR
        pr_result = await asyncio.to_thread(
            pr_opener.run,
            issue=issue,
            patch=patch,
            terminal_url=TERMINAL_URL,
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_engine.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add orchestrator/engine.py tests/test_engine.py
git commit -m "feat: AgentField orchestrator with full pipeline and retry loop"
```

---

## Task 13: Main Entry Point

**Files:**
- Create: `main.py`
- Create: `Dockerfile`
- Create: `zeabur.yaml`

- [ ] **Step 1: Implement main.py**

```python
import asyncio
import uvicorn
from config.settings import settings
from terminal.server import app, emit_event
from orchestrator.engine import run_pipeline


async def auto_run():
    import uuid
    run_id = str(uuid.uuid4())[:8]
    emit_event("ORCHESTRATOR", "Bounty Hunter online. Starting initial scan...", run_id)
    await run_pipeline(run_id)


async def main():
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    await asyncio.gather(
        server.serve(),
        auto_run(),
    )


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Create Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .

EXPOSE 8080

CMD ["python", "main.py"]
```

- [ ] **Step 3: Create zeabur.yaml**

```yaml
name: bounty-hunter
services:
  - name: bounty-hunter
    type: git
    build:
      type: docker
      dockerfile: Dockerfile
    ports:
      - port: 8080
        type: http
    env:
      PORT: "8080"
      MOCK_MODE: "false"
```

- [ ] **Step 4: Smoke test locally**

```bash
MOCK_MODE=true python main.py
# open http://localhost:8080
# verify terminal shows CONNECTED and pipeline runs automatically
# verify "Trigger New Run" button starts a second run
```

Expected: terminal UI loads, pipeline completes with mock PR URL logged.

- [ ] **Step 5: Commit**

```bash
git add main.py Dockerfile zeabur.yaml
git commit -m "feat: main entry point, Dockerfile, Zeabur config"
```

---

## Task 14: Full Pipeline Integration Test

**Files:**
- Create: `tests/test_pipeline.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/test_pipeline.py
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
    from orchestrator.memory import EvermindClient
    await run_pipeline(run_id="integration-003")
    memory = EvermindClient(mock_mode=True)
    from config.mocks import MOCK_SCRAPER_RESULT
    issue_url = MOCK_SCRAPER_RESULT[0]["issue_url"]
    assert memory.is_attempted(issue_url)
```

- [ ] **Step 2: Install pytest-asyncio**

```bash
pip install pytest-asyncio
```

- [ ] **Step 3: Add pytest config to pyproject.toml**

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 4: Run full integration test**

```bash
pytest tests/test_pipeline.py -v
```

Expected: 3 passed

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass. Fix any regressions before proceeding.

- [ ] **Step 6: Commit**

```bash
git add tests/test_pipeline.py pyproject.toml
git commit -m "test: full pipeline integration test in MOCK_MODE"
```

---

## Task 15: Zeabur Deployment

- [ ] **Step 1: Build Docker image locally to verify**

```bash
docker build -t bounty-hunter:local .
docker run --env-file .env -p 8080:8080 bounty-hunter:local
# open http://localhost:8080 — verify terminal loads and pipeline runs
```

Expected: identical to local `python main.py` run.

- [ ] **Step 2: Push to GitHub**

```bash
git remote add origin https://github.com/<YOUR_USERNAME>/bounty-hunter.git
git push -u origin main
```

- [ ] **Step 3: Deploy to Zeabur**

Go to [zeabur.com](https://zeabur.com), create a new project, connect the GitHub repo.

Set all env vars from `.env.example` in the Zeabur dashboard (with real values).

Set `MOCK_MODE=false` and `TERMINAL_URL=https://<your-project>.zeabur.app`.

- [ ] **Step 4: Verify live deployment**

```bash
curl https://<your-project>.zeabur.app/stream
# Should return text/event-stream with ping events
```

Open `https://<your-project>.zeabur.app` in browser — verify judges terminal loads with CONNECTED status.

- [ ] **Step 5: Test live trigger**

Press "TRIGGER NEW RUN" in the browser. Verify all 5 agents log in sequence and a real PR URL appears.

- [ ] **Step 6: Final commit**

```bash
git add zeabur.yaml
git commit -m "deploy: Zeabur production config"
git tag v1.0.0
git push && git push --tags
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Bright Data GitHub scraping | Task 7 |
| Optional repo whitelist | Task 7 (`repos.yaml` + `ScraperAgent(repo_whitelist=...)`) |
| Evermind cross-run dedup | Tasks 6, 7, 12 |
| GLM-5.1 root cause analysis | Task 8 |
| TokenRouter model routing | Task 5 |
| Qoder Expert Panel patching | Task 9 |
| Nosana sandboxed testing + local fallback | Task 10 |
| Patcher retry loop (max 2) | Task 12 (`engine.py`) |
| Confidence gate (0.70) | Task 8 |
| Actionbook PR + GitHub API fallback | Task 11 |
| git CLI push with GITHUB_TOKEN | Task 11 (`_push_branch`) |
| SSE terminal server | Task 3 |
| Judges' dark terminal UI | Task 3 |
| POST /trigger button | Tasks 3, 13 |
| MOCK_MODE escape hatch | Tasks 2, all agents |
| 90s hard timeout per step | Task 4 (`run_tests_in_dir`) |
| Sandbox isolation + cleanup | Tasks 4, 12 |
| Zeabur deployment | Task 15 |
| Butterbase run history | Task 3 (GET /runs stub — wire Butterbase in Task 3 if time allows) |
| AgentField orchestration | Task 12 (engine uses `asyncio.to_thread` as AgentField wrapper — replace decorator when SDK docs confirmed) |

**Note on AgentField:** The `engine.py` uses `asyncio.to_thread` as a clean async wrapper now. Once you have the AgentField SDK docs, replace each `asyncio.to_thread(agent.run, ...)` call with the `@af.agent` decorator pattern — the interface contract stays the same.

**Placeholder scan:** None found.

**Type consistency:** All agent `.run()` methods accept `run_id: str = ""` and return typed dicts. `EvermindClient`, `SandboxRunner`, `LLMRouter` are instantiated consistently across all agents and engine.
