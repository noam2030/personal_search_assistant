from fetcher import fetch_html
from cleaner import clean_html
from extractor import extract_content
from logger import write_debug_log
import db


def run_task(url: str, goal: str) -> str:
    """
    Orchestrates a single extraction task pipeline:
    1. Fetches HTML content from target URL and logs raw HTML immediately.
    2. Cleans and sanitizes the HTML into text and logs cleaned text.
    3. Extracts structured information matching the goal using Gemini AI and logs result.
    """
    raw_html = ""
    cleaned_text = ""
    result = ""

    print(f"[1/3] Fetching webpage: {url} ...")
    try:
        raw_html = fetch_html(url)
        write_debug_log(url, goal, raw_html=raw_html, cleaned_text=cleaned_text, result=result)
    except Exception as e:
        error_msg = f"Error fetching URL '{url}': {e}"
        write_debug_log(url, goal, raw_html=raw_html, cleaned_text=cleaned_text, result=result, error=error_msg)
        raise RuntimeError(error_msg) from e

    print("[2/3] Cleaning HTML content ...")
    cleaned_text = clean_html(raw_html)
    write_debug_log(url, goal, raw_html=raw_html, cleaned_text=cleaned_text, result=result)

    if not cleaned_text:
        error_msg = f"Cleaned webpage content is empty for URL '{url}'."
        write_debug_log(url, goal, raw_html=raw_html, cleaned_text=cleaned_text, result=result, error=error_msg)
        raise ValueError(error_msg)

    print(f"[3/3] Extracting information with Gemini AI for goal: '{goal}' ...\n")
    try:
        result = extract_content(cleaned_text, goal)
        write_debug_log(url, goal, raw_html=raw_html, cleaned_text=cleaned_text, result=result)
        return result
    except Exception as e:
        error_msg = f"Error during AI extraction: {e}"
        write_debug_log(url, goal, raw_html=raw_html, cleaned_text=cleaned_text, result=result, error=error_msg)
        raise RuntimeError(error_msg) from e


def run_task_by_id(task_id: int) -> dict:
    """
    Fetches a single task by task_id from the database, executes its extraction pipeline,
    updates the database with the latest result, and returns the updated task dict.
    Designed for Web API / UI execution triggers.
    """
    task = db.get_task(task_id)
    if not task:
        raise ValueError(f"Task with ID {task_id} not found.")

    print(f"--- Running Task [{task['id']}] '{task['name']}' ---")
    try:
        res_text = run_task(url=task["url"], goal=task["goal"])
        db.update_task_result(
            task_id=task["id"],
            status="SUCCESS",
            result_json=res_text,
            error=None,
        )
        print(f"✓ Task '{task['name']}' completed successfully.\n")
    except Exception as e:
        error_msg = str(e)
        db.update_task_result(
            task_id=task["id"],
            status="FAILED",
            result_json=None,
            error=error_msg,
        )
        print(f"✗ Task '{task['name']}' failed: {error_msg}\n")

    return db.get_task(task_id)


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
