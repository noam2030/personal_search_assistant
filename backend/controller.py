import os
import json
from typing import Dict, Any

from backend.agent.extract_content_agent import extract_content
from backend.logger import write_debug_log
from backend import db
from backend.notifier import send_telegram_message


def run_task(task_description: str) -> str:
    """
    Orchestrates a single task pipeline using Gemini AI with Google Search Grounding:
    1. Calls Gemini API with Google Search Grounding to perform web search and information extraction.
    2. Returns JSON string containing task_title and extracted items.
    """
    result = ""
    print(f"[1/1] Performing Natural Language Web Search for description: '{task_description}' ...")
    try:
        result = extract_content(task_description=task_description)
        write_debug_log(task_description=task_description, result=result)
        return result
    except Exception as e:
        error_msg = f"Error during AI search execution: {e}"
        write_debug_log(task_description=task_description, result=result, error=error_msg)
        raise RuntimeError(error_msg) from e


def extract_item_fingerprint(item: Any) -> str:
    """Generates a normalized canonical fingerprint for a search result item."""
    if not isinstance(item, dict):
        return str(item).strip().lower()

    link = ""
    for k in ["link", "url", "href"]:
        val = item.get(k)
        if val and isinstance(val, str) and val.strip():
            link = val.strip().lower().rstrip("/")
            break

    title = ""
    for k in ["title", "name", "heading", "event"]:
        val = item.get(k)
        if val and isinstance(val, str) and val.strip():
            title = " ".join(val.strip().lower().split())
            break

    if title and link:
        return f"{title}::{link}"
    if link:
        return link
    if title:
        return title
    return json.dumps(item, sort_keys=True).lower()


def parse_result_items(raw_result: Any) -> list:
    """Safely extracts items array from a raw JSON or markdown-wrapped result string."""
    if not raw_result:
        return []
    try:
        clean_raw = str(raw_result).replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_raw)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict):
            for k in ["items", "results", "events", "data"]:
                if isinstance(parsed.get(k), list):
                    return parsed[k]
    except Exception:
        pass
    return []


def diff_and_annotate_results(prev_raw_result: Any, new_raw_result: str) -> tuple[str, bool, int]:
    """
    Compares newly extracted result items against previous run results:
    - If prev_raw_result is None or empty: this is the first run / initial baseline.
      Items are saved as baseline (is_new = False), has_new_items = False, new_items_count = 0.
    - If prev_raw_result exists:
      Items not present in previous fingerprints are marked is_new = True.
      Items already present are marked is_new = False.
      has_new_items is True if any item is_new is True.
    Returns: (updated_result_json_str, has_new_items, new_items_count)
    """
    clean_raw = new_raw_result.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(clean_raw)
    except Exception:
        # Not valid JSON, return as-is without diffing
        return new_raw_result, False, 0

    is_dict = isinstance(parsed, dict)
    items = []
    items_key = "items"
    if is_dict:
        for k in ["items", "results", "events", "data"]:
            if isinstance(parsed.get(k), list):
                items = parsed[k]
                items_key = k
                break
    elif isinstance(parsed, list):
        items = parsed

    # Determine if this is the first run / baseline
    is_first_run = not prev_raw_result or not str(prev_raw_result).strip()

    has_new_items = False
    new_items_count = 0

    if is_first_run:
        # First run: establish initial baseline. Do not mark items as new, do not notify.
        for item in items:
            if isinstance(item, dict):
                item["is_new"] = False
        has_new_items = False
        new_items_count = 0
    else:
        # Subsequent run: compare with previous run's fingerprints
        prev_items = parse_result_items(prev_raw_result)
        prev_fingerprints = {extract_item_fingerprint(p) for p in prev_items}

        for item in items:
            if isinstance(item, dict):
                fp = extract_item_fingerprint(item)
                if fp not in prev_fingerprints:
                    item["is_new"] = True
                    new_items_count += 1
                else:
                    item["is_new"] = False

        has_new_items = new_items_count > 0

    if is_dict:
        parsed[items_key] = items
        parsed["has_new_items"] = has_new_items
        parsed["new_items_count"] = new_items_count
        updated_json_str = json.dumps(parsed, ensure_ascii=False)
    else:
        updated_json_str = json.dumps(items, ensure_ascii=False)

    return updated_json_str, has_new_items, new_items_count


def run_task_by_id(task_id: int) -> dict:
    """
    Fetches a task by ID, executes natural language search/extraction,
    diffs against baseline/previous results to tag new items (is_new),
    automatically updates task.name from Gemini's generated task_title,
    updates task results, and returns the updated task dict.
    """
    task = db.get_task(task_id)
    if not task:
        raise ValueError(f"Task with ID {task_id} not found.")

    task_desc = task.get("task_description", "")
    prev_raw_result = task.get("last_result")

    print(f"--- Running Task [{task['id']}] '{task['name']}' ---")
    has_new_items = False
    new_items_count = 0
    try:
        res_text = run_task(task_description=task_desc)

        # Diff against baseline/previous result and annotate is_new
        annotated_json, has_new_items, new_items_count = diff_and_annotate_results(
            prev_raw_result=prev_raw_result,
            new_raw_result=res_text,
        )

        # Try updating task.name if task_title was generated by Gemini
        try:
            parsed = json.loads(annotated_json)
            generated_title = parsed.get("task_title")
            if generated_title and isinstance(generated_title, str) and generated_title.strip():
                db.update_task_details(
                    task_id=task["id"],
                    name=generated_title.strip(),
                    task_description=task_desc,
                )
        except Exception:
            pass

        db.update_task_result(
            task_id=task["id"],
            status="SUCCESS",
            result_json=annotated_json,
            error=None,
        )
        print(f"✓ Task [{task['id']}] completed successfully (new items: {new_items_count}).\n")
    except Exception as e:
        error_msg = str(e)
        db.update_task_result(
            task_id=task["id"],
            status="FAILED",
            result_json=None,
            error=error_msg,
        )
        print(f"✗ Task [{task['id']}] failed: {error_msg}\n")

    updated = db.get_task(task_id)
    if updated:
        updated["has_new_items"] = has_new_items
        updated["new_items_count"] = new_items_count
    return updated


def run_user_tasks(user_id: str) -> list[dict]:
    """
    Fetches all persistent tasks for a user, executes each task via run_task_by_id,
    and returns the list of updated tasks with latest results.
    """
    tasks = db.list_tasks(user_id)
    if not tasks:
        print(f"No persistent tasks found for user '{user_id}'.")
        return []

    print(f"Found {len(tasks)} task(s) for user '{user_id}'. Starting execution...\n")
    results = []

    for idx, task in enumerate(tasks, 1):
        print(f"[Task {idx}/{len(tasks)}]")
        updated_task = run_task_by_id(task_id=task["id"])
        if updated_task:
            results.append(updated_task)

    return results


def handle_telegram_update(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    AI Agent Telegram Webhook Handler:
    Extracts message text, verifies chat_id, dispatches to Gemini AI Agent intent processor,
    and sends the formatted intelligent response back to Telegram.
    """
    from backend.agent.classify_agent import process_telegram_intent

    message = payload.get("message") or payload.get("edited_message")
    if not message or "text" not in message:
        return {"status": "ignored", "reason": "No text message in update"}

    chat_id = str(message.get("chat", {}).get("id"))
    text = message.get("text", "").strip()

    print(f"\n========================================")
    print(f"[Telegram AI Agent Dispatcher]")
    print(f"Chat ID: {chat_id}")
    print(f"Message Text: {text}")
    print(f"========================================\n")

    # Security check: verify incoming chat_id matches TELEGRAM_CHAT_ID (if configured)
    allowed_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if allowed_chat_id and chat_id != str(allowed_chat_id):
        print(f"[Webhook] Rejected unauthorized update from chat_id: {chat_id}")
        return {"status": "rejected", "reason": "Unauthorized chat_id"}

    user_id = os.getenv("DEFAULT_USER_ID", "noam")
    reply_text = process_telegram_intent(user_id=user_id, message_text=text)

    send_telegram_message(text=reply_text, chat_id=chat_id)
    return {"status": "ok", "chat_id": chat_id, "text": text}
