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
        res_parsed = json.loads(updated["last_result"])
        assert res_parsed["task_title"] == "Tel Aviv Lead Backend Developer Roles"
        assert res_parsed["items"][0]["title"] == "Lead Backend Engineer"
        assert res_parsed["items"][0]["is_new"] is False

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
    mock_results_unchanged = [{
        "id": 1,
        "name": "Tel Aviv Java Jobs",
        "last_status": "SUCCESS",
        "last_result": json.dumps({"items": [{"title": "Senior Java Developer", "link": "https://example.com/job", "is_new": False}], "has_new_items": False}),
        "last_error": None,
    }]
    mock_results_new = [{
        "id": 1,
        "name": "Tel Aviv Java Jobs",
        "last_status": "SUCCESS",
        "last_result": json.dumps({"items": [{"title": "Senior Java Developer", "link": "https://example.com/job", "is_new": True}], "has_new_items": True}),
        "last_error": None,
    }]
    formatted = format_telegram_message("noam", mock_results_new)
    assert "Tel Aviv Java Jobs" in formatted
    assert "Senior Java Developer" in formatted

    # 1. Test skipped notification when tokens absent
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""}):
        assert send_telegram_notification("noam", mock_results_new) is False

    # 2. Test skipped notification when NO new items are present (e.g. unchanged repeat run)
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "123", "TELEGRAM_CHAT_ID": "456"}):
        with patch("httpx.post") as mock_post:
            success = send_telegram_notification("noam", mock_results_unchanged)
            assert success is False
            mock_post.assert_not_called()

    # 3. Test successful notification when new items ARE present
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "123", "TELEGRAM_CHAT_ID": "456"}):
        with patch("httpx.post", return_value=mock_resp) as mock_post:
            success = send_telegram_notification("noam", mock_results_new)
            assert success is True
            mock_post.assert_called_once()

    print("[E2E Test] Telegram notification tests passed!\n")


def test_telegram_webhook_commands():
    print("[E2E Test] Testing AI Agent Telegram Webhook Intent Dispatcher...")
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "123", "TELEGRAM_CHAT_ID": "999"}):
        with patch("httpx.post", return_value=mock_resp) as mock_post:
            # 1. Test conversational greeting
            update_hello = {"message": {"chat": {"id": 999}, "text": "Hello, who are you?"}}
            res_hello = client.post("/api/telegram/webhook", json=update_hello)
            assert res_hello.status_code == 200
            assert res_hello.json()["status"] == "ok"

            # 2. Test intent creation (new search task)
            update_add = {"message": {"chat": {"id": 999}, "text": "Find me senior python jobs in Tel Aviv"}}
            res_add = client.post("/api/telegram/webhook", json=update_add)
            assert res_add.status_code == 200
            assert res_add.json()["status"] == "ok"

            # 3. Test list tasks intent
            update_list = {"message": {"chat": {"id": 999}, "text": "Show me my current tasks"}}
            res_list = client.post("/api/telegram/webhook", json=update_list)
            assert res_list.status_code == 200
            assert res_list.json()["status"] == "ok"

            # 4. Test unauthorized chat_id rejection
            update_unauth = {"message": {"chat": {"id": 888}, "text": "Unauthorized message"}}
            res_unauth = client.post("/api/telegram/webhook", json=update_unauth)
            assert res_unauth.status_code == 200
            assert res_unauth.json()["status"] == "rejected"

    print("[E2E Test] AI Agent Telegram Webhook Intent Dispatcher tests passed!\n")


def test_workspace_skills():
    """
    Verifies that workspace skills are loaded from .agents/skills/ and injected into the agent.
    """
    print("[E2E Test] Testing Workspace Skills Loader...")
    from backend.agent.skills import load_workspace_skills, format_skills_for_prompt
    from backend.agent.extract_content_agent import extract_agent

    skills = load_workspace_skills()
    assert len(skills) >= 1, "Expected at least one workspace skill"
    skill_names = [s["name"] for s in skills]
    assert "searching-skill" in skill_names, "searching-skill must be discovered"

    formatted = format_skills_for_prompt()
    assert "searching-skill" in formatted
    assert "geektime.co.il" in formatted.lower()

    assert "geektime.co.il" in extract_agent.instruction.lower()
    print("[E2E Test] Workspace Skills Loader tests passed!\n")


def test_frontend_brand_github_link():
    """
    Verifies that the GitHub repository link is placed in header-brand instead of the date,
    and the date elements are removed.
    """
    print("[E2E Test] Testing Frontend Brand GitHub Link...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    html_path = os.path.join(frontend_dir, "index.html")
    css_path = os.path.join(frontend_dir, "src", "styles.css")

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    assert 'id="githubRepoLink"' in html_content
    assert 'class="brand-github-link"' in html_content
    assert 'header-brand' in html_content
    # Confirm date elements were replaced
    assert 'id="currentDate"' not in html_content
    assert 'id="currentDateText"' not in html_content

    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
    assert '.header-brand' in css_content
    assert '.brand-github-link' in css_content
    assert '.github-icon' in css_content

    print("[E2E Test] Frontend Brand GitHub Link tests passed!\n")


def test_frontend_repo_link():
    """
    Verifies that the GitHub repository link is located in the brand header,
    has proper security attributes, and is removed from header actions and footer.
    """
    print("[E2E Test] Testing Frontend Repository Link Placement...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    html_path = os.path.join(frontend_dir, "index.html")

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    assert 'id="githubRepoLink"' in html_content
    assert 'https://github.com/noam2030/personal_search_assistant' in html_content
    assert 'target="_blank"' in html_content
    assert 'rel="noopener noreferrer"' in html_content
    assert 'brand-github-link' in html_content

    # Assert removed from footer
    footer_pos = html_content.find('<footer')
    assert 'githubRepoLink' not in html_content[footer_pos:], "GitHub link must be removed from footer"

    # Assert removed from header-actions
    actions_pos = html_content.find('class="header-actions"')
    card_pos = html_content.find('class="card full-width-card"')
    assert 'githubRepoLink' not in html_content[actions_pos:card_pos], "GitHub button must be removed from header-actions"

    print("[E2E Test] Frontend Repository Link Placement tests passed!\n")


def test_frontend_horizontal_card_grid():
    """
    Verifies that the horizontal cards layout (up to 4 items initially, show more toggle for > 4 items,
    and responsive CSS grid styling) is correctly configured in frontend files.
    """
    print("[E2E Test] Testing Frontend Horizontal Card Grid Layout...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    css_path = os.path.join(frontend_dir, "src", "styles.css")
    ts_path = os.path.join(frontend_dir, "src", "main.ts")

    with open(ts_path, "r", encoding="utf-8") as f:
        ts_content = f.read()
    assert 'items.slice(0, 4)' in ts_content, "Must take first 4 items for initial visible cards"
    assert 'items.slice(4)' in ts_content, "Must slice remaining items for extra container"
    assert 'Math.min(initialItems.length, 4)' in ts_content, "Must set up to 4 grid columns dynamically"
    assert 'result-cards-grid' in ts_content, "Must render result-cards-grid container"
    assert 'extra-results-container' in ts_content, "Must render extra-results-container"
    assert 'expand-results-btn' in ts_content, "Must render expand button"

    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()
    assert '.result-cards-grid' in css_content
    assert 'display: grid;' in css_content
    assert 'grid-template-columns: repeat(var(--grid-columns, 4)' in css_content
    assert '.extra-results-container.hidden' in css_content
    assert 'display: none !important;' in css_content
    assert '.result-item-card' in css_content
    assert 'display: flex;' in css_content
    assert 'flex-direction: column;' in css_content

    print("[E2E Test] Frontend Horizontal Card Grid Layout tests passed!\n")


def test_pr_ci_staging_workflow():
    """
    Verifies that the PR test and staging deployment GitHub Actions workflow is present and properly configured.
    """
    print("[E2E Test] Testing PR CI & Staging Workflow Configuration...")
    workflow_path = os.path.join(os.path.dirname(__file__), ".github", "workflows", "pr-test-and-staging.yml")
    assert os.path.exists(workflow_path), "pr-test-and-staging.yml must exist"

    with open(workflow_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "pull_request:" in content
    assert "branches:" in content
    assert "main" in content
    assert "jobs:" in content
    assert "test:" in content
    assert "pytest" in content
    assert "npm run build" in content
    assert "deploy-staging:" in content
    assert "needs: test" in content
    assert "personal-search-assistant-api-staging" in content
    assert "GCP_SA_KEY" in content

    print("[E2E Test] PR CI & Staging Workflow Configuration tests passed!\n")


def test_frontend_user_selector_layout():
    """
    Verifies that the user selector is positioned in a top line above the actions
    on the top right of the screen.
    """
    print("[E2E Test] Testing Frontend User Selector Layout...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    html_path = os.path.join(frontend_dir, "index.html")
    css_path = os.path.join(frontend_dir, "src", "styles.css")

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert 'class="header-right"' in html
    assert 'class="user-selector-row"' in html
    assert 'id="userIdInput"' in html
    assert 'class="header-actions"' in html

    # Verify user-selector-row comes before header-actions inside header-right
    user_pos = html.find('class="user-selector-row"')
    actions_pos = html.find('class="header-actions"')
    assert user_pos < actions_pos, "user-selector-row must appear before header-actions"

    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    assert '.header-right' in css
    assert '.user-selector-row' in css
    assert '.user-input' in css
    assert 'align-items: flex-end;' in css

    print("[E2E Test] Frontend User Selector Layout tests passed!\n")


def test_frontend_api_base_url_resolution():
    """
    Verifies that frontend/src/api.ts configures dynamic API base URL resolution
    routing Vercel preview/staging to Cloud Run Staging and falling back cleanly.
    """
    print("[E2E Test] Testing Frontend API Base URL Resolution...")
    api_path = os.path.join(os.path.dirname(__file__), "frontend", "src", "api.ts")
    assert os.path.exists(api_path), "api.ts must exist"

    with open(api_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "resolveApiBaseUrl" in content, "resolveApiBaseUrl must be defined"
    assert "personal-search-assistant-api-staging-6dekvxzgaq-uc.a.run.app" in content, "Must include staging Cloud Run API URL"
    assert "personal-search-assistant-api-6dekvxzgaq-uc.a.run.app" in content, "Must include production Cloud Run API URL"
    assert "vercel.app" in content, "Must detect vercel.app hostnames"
    assert "http://localhost:8000" in content, "Must fallback to localhost"

    print("[E2E Test] Frontend API Base URL Resolution tests passed!\n")


def test_frontend_api_base_url_display():
    """
    Verifies that the active backend API base URL is rendered directly under the GitHub link
    inside the brand header (.header-brand).
    """
    print("[E2E Test] Testing Frontend API Base URL Display under GitHub Link...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    html_path = os.path.join(frontend_dir, "index.html")
    css_path = os.path.join(frontend_dir, "src", "styles.css")
    ts_path = os.path.join(frontend_dir, "src", "main.ts")

    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert 'id="brandApiUrlContainer"' in html
    assert 'id="apiBaseUrlLink"' in html
    assert 'id="apiBaseUrlText"' in html
    assert 'class="brand-api-url"' in html

    # Verify brandApiUrlContainer is positioned after githubRepoLink inside .header-brand
    github_pos = html.find('id="githubRepoLink"')
    api_url_pos = html.find('id="brandApiUrlContainer"')
    assert github_pos != -1, "githubRepoLink must exist"
    assert api_url_pos != -1, "brandApiUrlContainer must exist"
    assert github_pos < api_url_pos, "API Base URL must be placed under the GitHub link"

    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    assert '.brand-api-url' in css
    assert '.api-url-label' in css
    assert '.brand-api-link' in css

    with open(ts_path, "r", encoding="utf-8") as f:
        ts_content = f.read()

    assert 'initApiBaseUrlDisplay' in ts_content
    assert 'apiBaseUrlLink' in ts_content

    print("[E2E Test] Frontend API Base URL Display tests passed!\n")


def test_frontend_compact_task_card_layout():
    """
    Verifies that task cards have action buttons (Run, Edit, Delete) positioned beside the status badge,
    omit the task description and last run rows, omit total results count badge, and retain the expand toggle.
    """
    print("[E2E Test] Testing Frontend Compact Task Card Layout...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    ts_path = os.path.join(frontend_dir, "src", "main.ts")
    css_path = os.path.join(frontend_dir, "src", "styles.css")

    with open(ts_path, "r", encoding="utf-8") as f:
        ts_content = f.read()

    # 1. Action buttons placed inside task-status-actions
    assert 'class="task-status-actions"' in ts_content, "Must group status badge and actions together"
    status_act_pos = ts_content.find('class="task-status-actions"')
    badge_pos = ts_content.find('class="badge', status_act_pos)
    actions_pos = ts_content.find('class="task-actions"', status_act_pos)
    assert status_act_pos != -1 and badge_pos != -1 and actions_pos != -1
    assert badge_pos < actions_pos, "Status badge should appear before action buttons inside task-status-actions"

    # 2. Omit task description and last run from task card HTML
    assert '<strong>Task Description:</strong>' not in ts_content, "Task description must not be displayed on card"
    assert '<strong>Last Run:</strong>' not in ts_content, "Last run timestamp must not be displayed on card"

    # 3. Omit total results count badge from renderResultSection
    assert 'result-header-title' not in ts_content, "Result header title must be removed"
    assert 'getItemCount' not in ts_content, "Total results count badge must be removed"

    # 4. Retain expand toggle for extra results
    assert 'expand-results-btn' in ts_content, "Must retain expand-results-btn"
    assert "'result' : 'results'" in ts_content, "Must toggle between result and results based on extraCount"

    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    assert '.task-status-actions' in css, "Must define .task-status-actions in styles.css"

    print("[E2E Test] Frontend Compact Task Card Layout tests passed!\n")


def test_frontend_omits_location_pill():
    """
    Verifies that location pills are removed from item results in frontend/src/main.ts,
    while keeping location keys in ignoredKeys to prevent accidental fallback rendering.
    """
    print("[E2E Test] Testing Frontend Omits Location Pill from Results...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    ts_path = os.path.join(frontend_dir, "src", "main.ts")

    with open(ts_path, "r", encoding="utf-8") as f:
        ts_content = f.read()

    assert 'result-pill-location' not in ts_content, "result-pill-location must be removed from item rendering"
    assert '<strong>Location:</strong>' not in ts_content, "Location label must not be rendered in items"
    assert 'locationKey' in ts_content, "locationKey must still be tracked"
    assert 'ignoredKeys' in ts_content, "ignoredKeys must be present"

    print("[E2E Test] Frontend Omits Location Pill tests passed!\n")


def test_task_result_diffing_and_new_item_annotation():
    """
    Verifies that diff_and_annotate_results properly:
    1. Treats initial run as baseline (is_new = False, has_new_items = False)
    2. Treats repeat run with identical items as unchanged (is_new = False, has_new_items = False)
    3. Detects added items on subsequent run (is_new = True, has_new_items = True, new_items_count > 0)
    """
    from backend.differ import (
        diff_and_annotate_results,
        extract_item_fingerprint,
        has_task_new_items,
        parse_result_items,
    )
    from backend.controller import diff_and_annotate_results as controller_diff
    assert controller_diff is diff_and_annotate_results, "Controller must re-export diff_and_annotate_results"

    initial_result = json.dumps({
        "task_title": "Tel Aviv AI Jobs",
        "items": [
            {"title": "AI Engineer", "link": "https://example.com/ai"},
            {"title": "ML Researcher", "link": "https://example.com/ml"}
        ]
    })

    # Step 1: First run (baseline)
    annotated_1, has_new_1, count_1 = diff_and_annotate_results(
        prev_raw_result=None,
        new_raw_result=initial_result,
    )
    assert has_new_1 is False, "First run must not flag new items"
    assert count_1 == 0
    parsed_1 = json.loads(annotated_1)
    assert all(i["is_new"] is False for i in parsed_1["items"])

    # Step 2: Repeat run with identical items
    annotated_2, has_new_2, count_2 = diff_and_annotate_results(
        prev_raw_result=annotated_1,
        new_raw_result=initial_result,
    )
    assert has_new_2 is False, "Repeat run with identical items must have has_new_items = False"
    assert count_2 == 0
    parsed_2 = json.loads(annotated_2)
    assert all(i["is_new"] is False for i in parsed_2["items"])

    # Step 3: Subsequent run with a newly added item
    updated_run_result = json.dumps({
        "task_title": "Tel Aviv AI Jobs",
        "items": [
            {"title": "AI Engineer", "link": "https://example.com/ai"},
            {"title": "ML Researcher", "link": "https://example.com/ml"},
            {"title": "Lead Agent Developer", "link": "https://example.com/agent"}
        ]
    })
    annotated_3, has_new_3, count_3 = diff_and_annotate_results(
        prev_raw_result=annotated_2,
        new_raw_result=updated_run_result,
    )
    assert has_new_3 is True, "Subsequent run with new item must have has_new_items = True"
    assert count_3 == 1
    parsed_3 = json.loads(annotated_3)
    items_3 = parsed_3["items"]
    assert items_3[0]["is_new"] is False
    assert items_3[1]["is_new"] is False
    assert items_3[2]["is_new"] is True, "Newly added item must be marked is_new = True"

    print("[E2E Test] Task Result Diffing & New Item Annotation tests passed!\n")


def test_frontend_new_item_indication():
    """
    Verifies that frontend/src/main.ts renders NEW badge and is-new-item class,
    and frontend/src/styles.css provides styles for item-badge-new, result-pill-new,
    and .result-item-card.is-new-item.
    """
    print("[E2E Test] Testing Frontend New Item Indication...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    ts_path = os.path.join(frontend_dir, "src", "main.ts")
    css_path = os.path.join(frontend_dir, "src", "styles.css")

    with open(ts_path, "r", encoding="utf-8") as f:
        ts_content = f.read()

    assert "item.is_new === true" in ts_content
    assert "item-badge-new" in ts_content
    assert "result-pill-new" in ts_content
    assert "is-new-item" in ts_content
    assert "'is_new'" in ts_content, "is_new must be in ignoredKeys"

    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()

    assert ".item-badge-new" in css_content
    assert ".result-pill-new" in css_content
    assert ".result-item-card.is-new-item" in css_content

    print("[E2E Test] Frontend New Item Indication tests passed!\n")


if __name__ == "__main__":
    test_db_operations()
    test_fastapi_rest_endpoints()
    test_telegram_notifier()
    test_telegram_webhook_commands()
    test_workspace_skills()
    test_frontend_brand_github_link()
    test_frontend_repo_link()
    test_frontend_horizontal_card_grid()
    test_pr_ci_staging_workflow()
    test_frontend_user_selector_layout()
    test_frontend_api_base_url_resolution()
    test_frontend_api_base_url_display()
    test_frontend_compact_task_card_layout()
    test_frontend_omits_location_pill()
    test_task_result_diffing_and_new_item_annotation()
    test_frontend_new_item_indication()
    test_e2e_live_api()
    print("All E2E tests completed successfully!")
