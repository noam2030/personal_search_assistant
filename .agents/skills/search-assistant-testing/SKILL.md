---
name: search-assistant-testing
description: >-
  Run end-to-end tests, verify database CRUD operations, validate FastAPI endpoints,
  and check backend services for the Personal Search Assistant project. Use whenever
  testing code changes, running E2E suites, or diagnosing backend service health.
---

# Personal Search Assistant Testing & Verification

A structured runbook for executing tests, validating backend services, and verifying components in the Personal Search Assistant project.

---

## 1. Environment & Prerequisites

Before running tests or launching services, ensure the environment is configured:

1. **Python Virtual Environment**:
   - Location: `.venv/` in the project root.
   - Use the environment binary: `.venv/bin/python`.
2. **Environment Variables (`.env`)**:
   - `GEMINI_API_KEY`: Required for live Google Search Grounding and intent dispatching.
   - `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`: Optional; mocked or skipped automatically in tests if omitted.
   - `DATABASE_URL`: Defaults to local SQLite (`assistant.db`) when not on Google Cloud Run (`K_SERVICE` unset).

---

## 2. Automated End-to-End Test Suite

The primary automated test script is [test_e2e.py](../../../test_e2e.py). It covers:

1. **Database CRUD (`backend/db.py`)**: Task creation, retrieval, updates, status changes, and deletion.
2. **FastAPI Endpoints (`backend/api.py`, `backend/main.py`)**:
   - `GET /api/health`
   - `GET /api/tasks` & `POST /api/tasks`
   - `PUT /api/tasks/{id}` & `DELETE /api/tasks/{id}`
   - `POST /api/tasks/{id}/run` (Task execution)
   - `POST /api/tasks/run-all` (Batch runner for Cloud Scheduler)
3. **Telegram Notification Module (`backend/notifier.py`)**: Message formatting and HTTP dispatching.
4. **AI Agent Telegram Webhook (`backend/agent/classify_agent.py`)**: Intent classification, conversational routing, and chat ID authorization.
5. **Live Search API**: Executes live web search with Gemini Search Grounding if `GEMINI_API_KEY` is present.

### Running the E2E Test Suite

You can execute the automated checks using the bundled helper script or via Python directly:

```bash
# Option A: Using the helper script
./.agents/skills/search-assistant-testing/scripts/run_checks.sh

# Option B: Direct python execution
.venv/bin/python test_e2e.py
```

### Expected Output
- All subtests output `[E2E Test] ... passed!`.
- Concludes with `All E2E tests completed successfully!` and exit code `0`.

---

## 3. Running Backend Services Locally

To run the backend API server for manual interaction or frontend integration:

### Start Uvicorn Server
```bash
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
| **Virtualenv** | Run `.venv/bin/python --version` | If missing, create via `python3 -m venv .venv` and install `requirements.txt`. |
| **Gemini API** | Check `echo $GEMINI_API_KEY` | Ensure valid key is present in `.env` or current shell. |
| **SQLite DB** | Check `assistant.db` permissions | If locked or corrupt, verify file permissions or reset for local dev. |
| **FastAPI Client** | Check `test_e2e.py` | If deprecated client warning appears, ensure compatible Starlette/FastAPI versions. |
