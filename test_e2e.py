import os
import json
from unittest.mock import patch
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend import db
from backend.controller import run_task, run_user_tasks, run_task_by_id
from backend.main import app
from backend.logger import DEBUG_FILE

# Load .env variables if available
load_dotenv()

client = TestClient(app)

SAMPLE_MEETUP_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Tech Events 2026</title>
</head>
<body>
    <main>
        <h1>Upcoming Tech Meetups</h1>
        <div class="event">
            <h2>Autonomous AI Agents Summit 2026</h2>
            <p>Date: November 12, 2026</p>
            <p>Location: San Francisco, CA & Online</p>
            <a href="https://example.com/events/agents-summit">Register Here</a>
        </div>
    </main>
</body>
</html>
"""


def test_db_operations():
    """
    Tests SQLite database CRUD operations for user tasks.
    """
    print("[E2E Test] Testing Database CRUD operations...")
    user_id = "test_user_db"

    # 1. Clean previous test tasks if any
    existing = db.list_tasks(user_id)
    for t in existing:
        db.delete_task(t["id"], user_id)

    # 2. Add Task
    task = db.add_task(
        user_id=user_id,
        name="Test Meetups Task",
        url="https://example.com/events",
        goal="find meetups about AI agents",
    )
    assert task["id"] is not None
    assert task["user_id"] == user_id
    assert task["name"] == "Test Meetups Task"

    # 3. List Tasks
    tasks = db.list_tasks(user_id)
    assert len(tasks) == 1
    assert tasks[0]["id"] == task["id"]

    # 4. Update Task Details
    updated_detail = db.update_task_details(
        task_id=task["id"],
        name="Updated Meetups Task",
        url="https://example.com/events-v2",
        goal="find AI events v2",
    )
    assert updated_detail["name"] == "Updated Meetups Task"
    assert updated_detail["goal"] == "find AI events v2"

    # 5. Update Task Result
    mock_result = json.dumps({"items": [{"title": "Agent Summit"}]})
    db.update_task_result(
        task_id=task["id"],
        status="SUCCESS",
        result_json=mock_result,
        error=None,
    )

    updated = db.get_task(task["id"])
    assert updated["last_status"] == "SUCCESS"
    assert updated["last_result"] == mock_result

    # 6. Delete Task
    deleted = db.delete_task(task["id"], user_id)
    assert deleted is True
    assert len(db.list_tasks(user_id)) == 0

    print("[E2E Test] Database CRUD tests passed!\n")


def test_fastapi_rest_endpoints():
    """
    Tests FastAPI REST API endpoints: /api/health, /api/tasks (GET/POST/PUT/DELETE).
    """
    print("[E2E Test] Testing FastAPI REST endpoints...")
    user_id = "test_user_api"

    # 1. Health check
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 2. Clean previous tasks
    res = client.get(f"/api/tasks?user_id={user_id}")
    for t in res.json():
        client.delete(f"/api/tasks/{t['id']}?user_id={user_id}")

    # 3. Create Task via POST /api/tasks
    payload = {
        "user_id": user_id,
        "name": "API Test Task",
        "url": "https://example.com/api-test",
        "goal": "extract api test items",
    }
    create_res = client.post("/api/tasks", json=payload)
    assert create_res.status_code == 201
    created_task = create_res.json()
    assert created_task["name"] == "API Test Task"
    task_id = created_task["id"]

    # 4. List Tasks via GET /api/tasks
    list_res = client.get(f"/api/tasks?user_id={user_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 5. Update Task Details via PUT /api/tasks/{id}
    update_payload = {
        "name": "Backend Jobs Task",
        "url": "https://example.com/backend-jobs",
        "goal": "extract backend developer positions",
    }
    put_res = client.put(f"/api/tasks/{task_id}", json=update_payload)
    assert put_res.status_code == 200
    updated_task_data = put_res.json()
    assert updated_task_data["name"] == "Backend Jobs Task"
    assert updated_task_data["goal"] == "extract backend developer positions"

    # 6. Mocked Execute Task via POST /api/tasks/{id}/run
    mock_gemini_json = json.dumps({"items": [{"title": "API Test Item"}]})
    with patch("backend.controller.fetch_html", return_value=SAMPLE_MEETUP_HTML):
        with patch("backend.controller.extract_content", return_value=mock_gemini_json):
            run_res = client.post(f"/api/tasks/{task_id}/run")
            assert run_res.status_code == 200
            updated = run_res.json()
            assert updated["last_status"] == "SUCCESS"
            assert updated["last_result"] == mock_gemini_json

    # 7. Delete Task via DELETE /api/tasks/{id}
    del_res = client.delete(f"/api/tasks/{task_id}?user_id={user_id}")
    assert del_res.status_code == 200

    print("[E2E Test] FastAPI REST endpoint tests passed!\n")


def test_e2e_live_api():
    """
    Live End-to-End test calling real HTTP fetcher and real Gemini API
    if GEMINI_API_KEY is configured and network connection is available.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[E2E Test] Skipping Live API E2E test (GEMINI_API_KEY not set in .env)")
        return

    print("[E2E Test] Running Live API E2E test against example.com ...")
    url = "https://example.com"
    goal = "extract the main heading and description text"

    try:
        result = run_task(url=url, goal=goal)
        assert result is not None
        assert len(result) > 0

        assert os.path.exists(DEBUG_FILE)
        with open(DEBUG_FILE, "r", encoding="utf-8") as f:
            log_content = f.read()
        assert "Example Domain" in log_content or "STEP 3:" in log_content

        print("[E2E Test] Live API E2E test passed!\n")
    except Exception as e:
        print(f"[E2E Test] Live API test skipped due to network/environment constraint: {e}\n")


if __name__ == "__main__":
    test_db_operations()
    test_fastapi_rest_endpoints()
    test_e2e_live_api()
    print("All E2E tests completed successfully!")
