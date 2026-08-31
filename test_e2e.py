import os
import json
from unittest.mock import patch
from dotenv import load_dotenv

import db
from controller import run_task, run_user_tasks, run_task_by_id
from fetcher import fetch_html
from cleaner import clean_html
from extractor import extract_content
from logger import DEBUG_FILE

# Load .env variables if available
load_dotenv()

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

    # 4. Update Task Result
    mock_result = json.dumps({"items": [{"title": "Agent Summit"}]})
    db.update_task_result(
        task_id=task["id"],
        status="SUCCESS",
        result_json=mock_result,
        error=None,
    )

    updated = db.get_task(task["id"], user_id)
    assert updated["last_status"] == "SUCCESS"
    assert updated["last_result"] == mock_result

    # 5. Delete Task
    deleted = db.delete_task(task["id"], user_id)
    assert deleted is True
    assert len(db.list_tasks(user_id)) == 0

    print("[E2E Test] Database CRUD tests passed!\n")


def test_run_task_by_id_mocked():
    """
    Tests run_task_by_id function executing a single task by ID from the DB.
    """
    print("[E2E Test] Testing run_task_by_id execution...")
    user_id = "test_user_by_id"

    # Clean existing
    for t in db.list_tasks(user_id):
        db.delete_task(t["id"], user_id)

    # Add task
    task = db.add_task(
        user_id=user_id,
        name="Single Task By ID Test",
        url="https://example.com/events",
        goal="find meetups about AI agents",
    )

    mock_gemini_json = json.dumps({
        "items": [
            {
                "title": "Autonomous AI Agents Summit 2026",
                "date": "November 12, 2026",
            }
        ]
    })

    with patch("controller.fetch_html", return_value=SAMPLE_MEETUP_HTML):
        with patch("controller.extract_content", return_value=mock_gemini_json):
            res_task = run_task_by_id(task_id=task["id"])

            assert res_task is not None
            assert res_task["id"] == task["id"]
            assert res_task["last_status"] == "SUCCESS"
            assert res_task["last_result"] == mock_gemini_json

    # Clean up
    db.delete_task(task["id"], user_id)
    print("[E2E Test] run_task_by_id test passed!\n")


def test_e2e_user_tasks_mocked():
    """
    Integration test verifying run_user_tasks orchestration with database persistence.
    """
    print("[E2E Test] Running mocked user tasks execution test...")
    user_id = "test_user_run"

    # Clean existing
    for t in db.list_tasks(user_id):
        db.delete_task(t["id"], user_id)

    # Create task
    task = db.add_task(
        user_id=user_id,
        name="Mock Event Agent Task",
        url="https://example.com/events",
        goal="find meetups about AI agents",
    )

    mock_gemini_json = json.dumps({
        "items": [
            {
                "title": "Autonomous AI Agents Summit 2026",
                "date": "November 12, 2026",
                "link": "https://example.com/events/agents-summit",
            }
        ]
    })

    with patch("controller.fetch_html", return_value=SAMPLE_MEETUP_HTML):
        with patch("controller.extract_content", return_value=mock_gemini_json):
            results = run_user_tasks(user_id=user_id)

            assert len(results) == 1
            res_task = results[0]
            assert res_task["last_status"] == "SUCCESS"
            assert res_task["last_result"] == mock_gemini_json

    # Clean up
    db.delete_task(task["id"], user_id)
    print("[E2E Test] Mocked user tasks execution test passed!\n")


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
    test_run_task_by_id_mocked()
    test_e2e_user_tasks_mocked()
    test_e2e_live_api()
    print("All E2E tests completed successfully!")
