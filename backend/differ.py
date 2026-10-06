import json
from typing import Any, Dict, List, Optional, Tuple


def extract_item_fingerprint(item: Any) -> str:
    """
    Generates a normalized canonical fingerprint for a search result item.
    Combines normalized title and URL/link when available to ensure stable deduplication.
    """
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


def parse_result_items(raw_result: Any) -> List[Any]:
    """
    Safely extracts items array from a raw JSON or markdown-wrapped result string.
    """
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


def diff_and_annotate_results(prev_raw_result: Any, new_raw_result: str) -> Tuple[str, bool, int]:
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


def has_task_new_items(task: Dict[str, Any]) -> bool:
    """
    Determines if a task execution produced new items compared to the baseline/previous run.
    """
    if task.get("has_new_items") is True:
        return True

    raw_result = task.get("last_result")
    if not raw_result:
        return False

    try:
        clean_raw = str(raw_result).replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_raw)
        if isinstance(parsed, dict) and parsed.get("has_new_items") is True:
            return True
        items = []
        if isinstance(parsed, list):
            items = parsed
        elif isinstance(parsed, dict):
            for key in ["items", "results", "events", "data"]:
                if isinstance(parsed.get(key), list):
                    items = parsed[key]
                    break
        return any(isinstance(i, dict) and i.get("is_new") is True for i in items)
    except Exception:
        return False
