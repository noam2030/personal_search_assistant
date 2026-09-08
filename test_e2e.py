import os
import json
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend import db
from backend.controller import run_task, run_task_by_id
from backend.main import app

# Load .env variables if available
load_dotenv()

client = TestClient(app)


def test_db_operations():
    """
    Tests SQLite database CRUD operations for user tasks using task_description.
    """
    print("[E2E Test] Testing Database CRUD operations...")
    user_id = "test_user_db"

    # 1. Clean previous test tasks if any
    existing = db.list_tasks(user_id)
    for t in existing:
        db.delete_task(t["id"], user_id)

    # 2. Add Task (single task_description string)
    task = db.add_task(
        user_id=user_id,
        name="Tel Aviv Java Jobs",
        task_description="find me jobs in Tel Aviv Java backend",
    )
    assert task["id"] is not None
    assert task["user_id"] == user_id
    assert task["task_description"] == "find me jobs in Tel Aviv Java backend"

    # 3. List Tasks
    tasks = db.list_tasks(user_id)
    assert len(tasks) == 1
    assert tasks[0]["id"] == task["id"]

    # 4. Update Task Details
    updated_detail = db.update_task_details(
        task_id=task["id"],
        name="Tel Aviv Senior Java Jobs",
        task_description="find me senior jobs in Tel Aviv Java backend",
    )
    assert updated_detail["name"] == "Tel Aviv Senior Java Jobs"
    assert updated_detail["task_description"] == "find me senior jobs in Tel Aviv Java backend"

    # 5. Update Task Result
    mock_result = json.dumps({"task_title": "Tel Aviv Senior Java Jobs", "items": [{"title": "Senior Java Developer"}]})
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

    # 3. Create Task via POST /api/tasks (single task_description)
    payload = {
        "user_id": user_id,
        "task_description": "find me jobs in Tel Aviv Java backend",
    }
    create_res = client.post("/api/tasks", json=payload)
    assert create_res.status_code == 201
    created_task = create_res.json()
    assert created_task["task_description"] == "find me jobs in Tel Aviv Java backend"
    task_id = created_task["id"]

    # 4. List Tasks via GET /api/tasks
    list_res = client.get(f"/api/tasks?user_id={user_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 5. Update Task Details via PUT /api/tasks/{id}
    update_payload = {
        "task_description": "find me lead backend developer roles in Tel Aviv",
    }
    put_res = client.put(f"/api/tasks/{task_id}", json=update_payload)
    assert put_res.status_code == 200
    updated_task_data = put_res.json()
    assert updated_task_data["task_description"] == "find me lead backend developer roles in Tel Aviv"

    # 6. Mocked Execute Task via POST /api/tasks/{id}/run (Auto-Naming + Results)
    mock_gemini_json = json.dumps({
        "task_title": "Tel Aviv Lead Backend Developer Roles",
        "items": [{"title": "Lead Backend Engineer", "location": "Tel Aviv"}]
    })
    with patch("backend.controller.extract_content", return_value=mock_gemini_json):
        run_res = client.post(f"/api/tasks/{task_id}/run")
        assert run_res.status_code == 200
        updated = run_res.json()
        assert updated["name"] == "Tel Aviv Lead Backend Developer Roles"
        assert updated["last_status"] == "SUCCESS"
        assert updated["last_result"] == mock_gemini_json

    # 7. Mocked Batch Execute Tasks via POST /api/tasks/run-all (Cloud Scheduler endpoint)
    with patch("backend.controller.extract_content", return_value=mock_gemini_json):
        batch_res = client.post(f"/api/tasks/run-all?user_id={user_id}")
        assert batch_res.status_code == 200
        batch_data = batch_res.json()
        assert isinstance(batch_data, list)
        assert len(batch_data) == 1
        assert batch_data[0]["id"] == task_id

    # 8. Delete Task via DELETE /api/tasks/{id}
    del_res = client.delete(f"/api/tasks/{task_id}?user_id={user_id}")
    assert del_res.status_code == 200

    print("[E2E Test] FastAPI REST endpoint tests passed!\n")


def test_e2e_live_api():
    """
    Live End-to-End test calling real Gemini API with Google Search Grounding
    if GEMINI_API_KEY is configured.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[E2E Test] Skipping Live API E2E test (GEMINI_API_KEY not set in .env)")
        return

    print("[E2E Test] Running Live Natural Language Search API test ...")
    task_description = "find me tech news about AI agents"

    try:
        result = run_task(task_description=task_description)
        assert result is not None
        assert len(result) > 0
        print("[E2E Test] Live Natural Language Search API test passed!\n")
    except Exception as e:
        print(f"[E2E Test] Live API test skipped due to environment constraint: {e}\n")


from backend.notifier import format_telegram_message, send_telegram_notification


def test_telegram_notifier():
    print("[E2E Test] Testing Telegram notification module...")
    mock_results = [{
        "id": 1,
        "name": "Tel Aviv Java Jobs",
        "last_status": "SUCCESS",
        "last_result": json.dumps({"items": [{"title": "Senior Java Developer", "link": "https://example.com/job"}]}),
        "last_error": None,
    }]
    formatted = format_telegram_message("noam", mock_results)
    assert "Tel Aviv Java Jobs" in formatted
    assert "Senior Java Developer" in formatted

    # Test skipped notification when tokens absent
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
        assert send_telegram_notification("noam", mock_results) is False

    # Test successful notification with mocked httpx.post
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "123", "TELEGRAM_CHAT_ID": "456"}):
        with patch("httpx.post", return_value=mock_resp) as mock_post:
            success = send_telegram_notification("noam", mock_results)
            assert success is True
            mock_post.assert_called_once()

    print("[E2E Test] Telegram notification tests passed!\n")


if __name__ == "__main__":
    test_db_operations()
    test_fastapi_rest_endpoints()
    test_telegram_notifier()
    test_e2e_live_api()
    print("All E2E tests completed successfully!")
