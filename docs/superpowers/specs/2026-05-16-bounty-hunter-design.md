# Bounty Hunter — Autonomous OSS Contributor
**Design Spec | Agent Forge Hackathon | 2026-05-16**

---

## Overview

An autonomous, headless AI agent that discovers open Python bugs on GitHub, writes precise code fixes using a multi-agent engineering panel, verifies fixes with automated tests, and opens formal pull requests — all without human intervention. Judges watch the entire process live via a streaming terminal UI.

**Core value proposition:** OSS maintainers get 100s of issues and zero autonomous contributors. This agent is their first.

---

## 1. Agent Roles

Five specialized agents registered as AgentField microservices. Each has one job and one output contract.

| Agent | Sponsor Tool | Input | Output |
|---|---|---|---|
| Scraper | Bright Data | search config | `[{repo_url, issue_url, issue_title, issue_body, issue_number}]` |
| Analyst | GLM-5.1 via TokenRouter | issue + cloned repo | `{root_cause, affected_files[], fix_approach, confidence_score}` |
| Patcher | Qoder Expert Panel | analysis | `{patch_diff, test_code, explanation}` |
| Verifier | Nosana | patch | `{passed: bool, test_output, retry_count}` |
| PR Opener | Actionbook | verified patch | `{pr_url, comment_posted: bool}` |

**Cross-cutting concerns:**
- **AgentField**: `@agent` decorator on all five agents; shared memory bus; async execution
- **Evermind**: long-term memory — dedup attempted issues, persist successful fix patterns, remember trusted repos
- **TokenRouter**: unified LLM routing — GLM-5.1 for deep reasoning, Qwen for fast classification
- **Butterbase**: run history DB + auth for the judges' terminal

---

## 2. File Structure

```
bounty-hunter/
├── agents/
│   ├── __init__.py
│   ├── scraper.py          # Bright Data + GitHub search + Qwen scoring
│   ├── analyst.py          # git clone + GLM-5.1 root cause analysis
│   ├── patcher.py          # Qoder Expert Panel: Senior Engineer + Test Writer
│   ├── verifier.py         # Nosana pytest runner with retry loop
│   └── pr_opener.py        # Actionbook GitHub PR automation
├── orchestrator/
│   ├── __init__.py
│   ├── engine.py           # AgentField coordinator + pipeline routing
│   └── memory.py           # Evermind integration
├── router/
│   ├── __init__.py
│   └── llm.py              # TokenRouter unified LLM interface
├── terminal/
│   ├── __init__.py
│   ├── server.py           # FastAPI SSE backend + Butterbase run history
│   └── static/
│       └── index.html      # Judges' live terminal UI
├── sandbox/
│   ├── __init__.py
│   └── runner.py           # git clone + venv creation + pytest execution
├── config/
│   ├── __init__.py
│   ├── settings.py         # env var loading
│   ├── mocks.py            # MOCK_MODE=true pre-baked responses
│   └── repos.yaml          # optional repo whitelist
├── tests/
│   └── test_pipeline.py
├── main.py                 # entry point
├── pyproject.toml
├── Dockerfile
├── zeabur.yaml
└── .env.example
```

---

## 3. End-to-End Data Flow

```
main.py
  │
  ▼
[Orchestrator] — AgentField
  │  boots → registers all 5 agents
  │  loads Evermind memory (attempted issues, known repos)
  │  starts SSE terminal server on :8080
  │
  ▼
[Scraper Agent] — Bright Data
  │  queries: github.com/search?q=label:bug+language:python+state:open
  │  if repos.yaml present → filter to whitelist
  │  Qwen scores candidates by fixability (has error trace, small scope, test suite exists)
  │  Evermind dedup: strips already-attempted issues
  │  selects top candidate
  │
  ▼  {repo_url, issue_url, issue_title, issue_body, issue_number}
  │
[Analyst Agent] — GLM-5.1 via TokenRouter
  │  sandbox/runner.py: git clone → /tmp/sandbox/{run_id}/
  │  GLM-5.1: reads issue_body + file tree → identifies root cause + affected files
  │  confidence_score < 0.7 → emit "skipping: ambiguous" → loop back to Scraper
  │  confidence_score ≥ 0.7 → proceed
  │
  ▼  {root_cause, affected_files[], fix_approach, confidence_score}
  │
[Patcher Agent] — Qoder Expert Panel
  │  Expert Panel: Senior Engineer writes fix, Test Writer writes/extends tests
  │  outputs unified git diff patch
  │
  ▼  {patch_diff, test_code, explanation}
  │
[Verifier Agent] — Nosana
  │  applies patch in /tmp/sandbox/{run_id}/
  │  packages sandbox into Nosana job spec (Docker: python:3.11-slim + pytest)
  │  submits job via Nosana API → polls for stdout result
  │  fallback: local subprocess pytest if Nosana unavailable
  │  tests fail → send failure trace back to Patcher (max 2 retries)
  │  tests pass → proceed
  │
  ▼  {passed: true, test_output}
  │
[PR Opener Agent] — Actionbook + git CLI
  │  git CLI (GITHUB_TOKEN): push patch branch to fork
  │  Actionbook: navigates GitHub UI → clicks "Fork" → fills PR form → submits
  │  PR body: issue ref + explanation + full diff + judges terminal URL
  │
  ▼  {pr_url}
  │
[Orchestrator]
  │  Evermind: writes {issue_url, pr_url, outcome: success} to long-term memory
  │  SSE terminal: broadcasts "RUN COMPLETE — PR: {pr_url}"
  └─ loop to next issue or halt
```

---

## 4. Sponsor Tool Integration Map

### Load-bearing (pipeline breaks without these)
| Tool | Role |
|---|---|
| AgentField | `@agent` decorator, shared memory bus, async orchestration |
| Bright Data | GitHub search scraping, bypasses rate limits |
| GLM-5.1 (Z.ai) | Deep code reasoning in Analyst Agent |
| Qoder | Expert Panel Mode in Patcher Agent |
| Actionbook | Browser automation to fork repo + fill + submit GitHub PR form |
| Zeabur | Hosts the agent + judges' terminal |

### Meaningful (real value, gracefully degradable)
| Tool | Role |
|---|---|
| Evermind | Cross-run memory: dedup, fix patterns, repo trust |
| Nosana | Sandboxed pytest execution on GPU node |
| TokenRouter | Unified LLM routing + caching across all agents |

### Enhancement (impressive, not critical path)
| Tool | Role |
|---|---|
| Qwen Cloud | Candidate scoring in Scraper Agent |
| Butterbase | Run history DB + "View past runs" in terminal |

---

## 5. Live Terminal Design

**URL:** `{project}.zeabur.app` — shared with judges before demo

**Backend:** FastAPI with SSE endpoint at `GET /stream`
- Each agent calls `emit_event(agent_name, message)` — one function, zero boilerplate
- Events buffered 60s so late-joining browsers catch up mid-run
- `POST /trigger` — judges press a button, agent starts a fresh run live

**UI mockup:**
```
╔══════════════════════════════════════════════════════════════════╗
║  BOUNTY HUNTER  //  agent-forge-2026  //  run: a3f9-bc12        ║
╠══════════════════════════════════════════════════════════════════╣
║  [10:42:01] SCRAPER    ▶  Bright Data: querying GitHub...       ║
║  [10:42:03] SCRAPER    ▶  Found 47 open Python bugs             ║
║  [10:42:04] SCRAPER    ▶  Qwen scored 47 → top candidate:       ║
║             repo: psf/requests  issue #6821 "json decode error" ║
║  [10:42:05] MEMORY     ▶  Evermind: 0 prior attempts on repo    ║
║  [10:42:06] ANALYST    ▶  Cloning psf/requests to sandbox...    ║
║  [10:42:09] ANALYST    ▶  GLM-5.1 reading issue + file tree     ║
║  [10:42:14] ANALYST    ▶  Root cause: models/encoders.py:112    ║
║             confidence: 0.91  ✓ proceeding                      ║
║  [10:42:15] PATCHER    ▶  Convening Expert Panel...             ║
║  [10:42:15] PATCHER    ▶  → Senior Engineer analyzing patch     ║
║  [10:42:19] PATCHER    ▶  → Test Writer extending test suite    ║
║  [10:42:23] PATCHER    ▶  Patch ready: +14 lines / -3 lines     ║
║  [10:42:24] VERIFIER   ▶  Submitting to Nosana GPU node...      ║
║  [10:42:31] VERIFIER   ▶  pytest: 47 passed, 0 failed  ✓       ║
║  [10:42:32] PR OPENER  ▶  Actionbook: navigating GitHub...      ║
║  [10:42:38] PR OPENER  ▶  Fork created, branch pushed           ║
║  [10:42:41] PR OPENER  ▶  PR opened: github.com/psf/requests/   ║
║             pull/6834  ✓                                         ║
║  [10:42:42] COMPLETE   ▶  Run a3f9-bc12 finished in 41s         ║
║─────────────────────────────────────────────────────────────────║
║  PAST RUNS   [View History ↗]        TRIGGER NEW RUN  [▶ Run]   ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 6. Error Handling & Reliability

**Three rules:**
1. Terminal never goes blank — every error is a visible log line
2. Pipeline never hard-crashes — every agent has a fallback path
3. "Trigger New Run" button always works

**Failure → Response map:**

| Failure | Where | Response |
|---|---|---|
| Bright Data rate limit | Scraper | Retry 3× with 5s backoff → fall back to Evermind cached issue list |
| No issues pass confidence gate | Analyst | Loop to Scraper, next candidate (max 5 attempts) |
| GLM-5.1 timeout | Analyst | TokenRouter auto-routes to Qwen, logs "switching model" |
| Patch breaks tests | Verifier | Failure trace → Patcher retry ×2 → mark "too complex", move on |
| Nosana unavailable | Verifier | Fall back to local subprocess pytest |
| Actionbook DOM fail | PR Opener | Fall back to PyGitHub REST API |
| Zeabur deploy unhealthy | DevOps | Agent continues, logs warning |
| Evermind write fails | Memory | Log warning, continue — enhancement tier |

**Sandbox isolation:**
- Every run clones to `/tmp/sandbox/{run_id}/` — fully isolated
- Destroyed after Verifier completes regardless of outcome
- pytest runs in a fresh `venv` — no pollution between runs
- 90s hard timeout per agent step

**`MOCK_MODE=true` escape hatch:**
- Pre-baked responses for every sponsor API in `config/mocks.py`
- Identical code path and terminal output
- Flip to `MOCK_MODE=false` on demo day — everything goes live

---

## 7. Environment Variables

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

# Z.ai / GLM-5.1
ZAI_API_KEY=

# Qoder
QODER_API_KEY=

# TokenRouter
TOKENROUTER_API_KEY=

# Evermind
EVERMIND_API_KEY=

# Nosana
NOSANA_API_KEY=

# Zeabur
ZEABUR_API_KEY=
ZEABUR_PROJECT_ID=

# Butterbase
BUTTERBASE_API_KEY=

# GitHub (for git push + PyGitHub fallback)
GITHUB_TOKEN=
GITHUB_USERNAME=

# App
MOCK_MODE=false
LOG_LEVEL=INFO
PORT=8080
```

---

## 8. Deployment

**Zeabur deployment via `zeabur.yaml`:**
- Single service: the FastAPI terminal server + agent orchestrator in one process
- Agents run as async tasks within the same process (AgentField manages concurrency)
- Public URL exposed for judges

**Local development:**
```bash
cp .env.example .env  # fill in keys
MOCK_MODE=true python main.py  # full pipeline, zero API cost
```

---

*Spec reviewed: no placeholders, no contradictions, no ambiguous requirements. Scope is appropriate for a single implementation plan.*
