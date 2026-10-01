---
name: search-assistant-testing
description: >-
  Run end-to-end tests, verify database CRUD operations, validate FastAPI endpoints,
  and check backend services for the Personal Search Assistant project. Use whenever
  testing code changes, running E2E suites, or diagnosing backend service health.
---

# Personal Search Assistant Testing & Verification

A structured runbook for executing tests, validating backend services, and verifying components in the Personal Search Assistant project using `uv` and `.venv`.

---

## 1. Environment & Prerequisites

Before running tests or launching services, ensure the environment is configured:

1. **Python Virtual Environment & uv**:
   - Environment Manager: `uv` (exclusively manages `.venv/`).
   - Run tests and tools via: `uv run pytest` or `.venv/bin/pytest`.
   - Never use legacy `venv/` or system-wide python.
2. **Environment Variables (`.env`)**:
   - `GEMINI_API_KEY`: Required for live Google Search Grounding and intent dispatching.
   - `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`: Optional; mocked or skipped automatically in tests if omitted.
   - `DATABASE_URL`: Defaults to local SQLite (`assistant.db`) when not on Google Cloud Run (`K_SERVICE` unset).

> [!IMPORTANT]
> **MANDATORY: Run Tests via uv or Virtual Environment (`uv run pytest` / `.venv/bin/pytest`)**
> Never run global `pytest` or system-wide python test runners. Always execute tests strictly through `uv` or the `.venv` virtual environment binary:
> ```bash
> uv run pytest test_e2e.py
> ```
> (or `.venv/bin/pytest test_e2e.py`). Global tools or legacy `venv` may lack dependencies or fail with environment mismatches.

---

## 2. Automated End-to-End Test Suite

The primary automated test suite is [test_e2e.py](../../../test_e2e.py). It covers:

1. **Database CRUD (`backend/db.py`)**: Task creation, retrieval, updates, status changes, and deletion.
2. **FastAPI Endpoints (`backend/api.py`, `backend/main.py`)**:
   - `GET /api/health`
   - `GET /api/tasks` & `POST /api/tasks`
   - `PUT /api/tasks/{id}` & `DELETE /api/tasks/{id}`
   - `POST /api/tasks/{id}/run` (Task execution)
   - `POST /api/tasks/run-all` (Batch runner for Cloud Scheduler)
3. **Telegram Notification Module (`backend/notifier.py`)**: Message formatting and HTTP dispatching.
4. **Google ADK Agent Telegram Webhook (`backend/agent/classify_agent.py`)**: Intent classification, conversational routing, and chat ID authorization using Google ADK.
5. **Live Search API (`backend/agent/extract_content_agent.py`)**: Executes live web search with Google ADK Agent and Google Search Grounding if `GEMINI_API_KEY` is present.

### Running the Test Suite

> [!CAUTION]
> Always execute test commands via `uv run pytest` or the project's virtual environment (`.venv/bin/pytest`). Do NOT use system `pytest` or legacy `venv`.

```bash
# Option A: Execute all tests using uv (Primary & Recommended)
uv run pytest test_e2e.py

# Option B: Run with verbose output
uv run pytest test_e2e.py -v

# Option C: Run a specific test function
uv run pytest test_e2e.py -k "test_telegram_webhook_commands" -v

# Option D: Direct execution with .venv pytest binary
.venv/bin/pytest test_e2e.py

# Option E: Using the bundled runner script
./.agents/skills/search-assistant-testing/scripts/run_checks.sh
```

### Expected Output
- Pytest collects all test cases and reports passes: `===== 5 passed in ... =====`.
- Concludes with exit code `0`.

---

## 3. Running Backend Services Locally

To run the backend API server for manual interaction or frontend integration:

### Start Uvicorn Server via uv
```bash
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
# Or via .venv directly:
.venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Health Check Verification
```bash
curl -s http://localhost:8000/api/health | jq .
```
Expected response:
```json
{
  "status": "ok"
}
```

### Listing Tasks via API
```bash
curl -s "http://localhost:8000/api/tasks?user_id=default_user" | jq .
```

---

## 4. Verification & Diagnostics Checklist

When debugging or verifying fixes:

| Component | Verification Step | Common Issue / Resolution |
| :--- | :--- | :--- |
| **Virtualenv & uv** | Run `uv run python --version` or `.venv/bin/python --version` | If missing, create via `uv venv .venv` and install `uv pip install -r requirements.txt`. Ensure no legacy `venv/` dir exists. |
| **Gemini API** | Check `echo $GEMINI_API_KEY` | Ensure valid key is present in `.env` or current shell. Exported to `GOOGLE_API_KEY` for Google ADK. |
| **SQLite DB** | Check `assistant.db` permissions | If locked or corrupt, verify file permissions or reset for local dev. |
| **FastAPI Client** | Check `test_e2e.py` | If deprecated client warning appears, ensure compatible Starlette/FastAPI versions. |
