import json
import re
from typing import Any, Dict, List, Optional, Tuple


def normalize_url(url: str) -> str:
    """
    Normalizes a URL by stripping protocol, www subdomain, tracking query parameters,
    and trailing slashes to enable stable comparisons across LLM extractions.
    """
    if not url or not isinstance(url, str):
        return ""
    u = url.strip().lower()
    # Strip protocol
    u = re.sub(r"^https?://", "", u)
    # Strip www.
    u = re.sub(r"^www\.", "", u)
    # Strip common tracking query parameters
    u = re.sub(r"(\?|&)(utm_[^&]+|ref=[^&]+|fbclid=[^&]+|gclid=[^&]+)", "", u)
    u = u.rstrip("?&")
    # Strip trailing slash
    u = u.rstrip("/")
    return u


def normalize_title(title: str) -> str:
    """
    Normalizes a title string by lowercasing, stripping punctuation,
    and condensing whitespace.
    """
    if not title or not isinstance(title, str):
        return ""
    t = re.sub(r"[^\w\s]", " ", title.lower())
    return " ".join(t.split())


def is_generic_url(norm_url: str) -> bool:
    """
    Checks if a normalized URL is just a root domain or a generic landing/search page.
    For generic URLs, URL equality alone is not sufficient to declare two items identical.
    """
    if not norm_url:
        return True
    parts = norm_url.split("/", 1)
    if len(parts) == 1 or not parts[1].strip():
        return True
    path = parts[1].strip("/")
    generic_paths = {
        "about",
        "careers",
        "jobs",
        "deals",
        "events",
        "applications",
        "search",
        "results",
        "find",
        "deals_search.asp",
        "index.html",
    }
    if path in generic_paths or any(path.startswith(f"{gp}/") for gp in generic_paths):
        return True
    return False


def is_same_item(item1: Any, item2: Any) -> bool:
    """
    Determines whether two search result items refer to the same logical result.
    Accounts for LLM variations across runs:
    - Normalizes URLs (protocol, www, tracking parameters, trailing slashes).
    - Normalizes titles (punctuation, case, excess whitespace).
    - Checks specific URL identity or title token overlap.
    """
    if not isinstance(item1, dict) or not isinstance(item2, dict):
        return str(item1).strip().lower() == str(item2).strip().lower()

    # Extract title candidates
    title1 = ""
    for k in ["title", "name", "heading", "event"]:
        val = item1.get(k)
        if val and isinstance(val, str) and val.strip():
            title1 = val
            break

    title2 = ""
    for k in ["title", "name", "heading", "event"]:
        val = item2.get(k)
        if val and isinstance(val, str) and val.strip():
            title2 = val
            break

    # Extract link candidates
    link1 = ""
    for k in ["link", "url", "href"]:
        val = item1.get(k)
        if val and isinstance(val, str) and val.strip():
            link1 = val
            break

    link2 = ""
    for k in ["link", "url", "href"]:
        val = item2.get(k)
        if val and isinstance(val, str) and val.strip():
            link2 = val
            break

    t1 = normalize_title(title1)
    t2 = normalize_title(title2)
    u1 = normalize_url(link1)
    u2 = normalize_url(link2)

    # 1. Exact normalized title match (covers identical listings with different/generic URLs)
    if t1 and t2 and t1 == t2:
        return True

    # 2. Specific non-generic URL match (same specific page/deal/event URL)
    if u1 and u2 and not is_generic_url(u1) and not is_generic_url(u2):
        if u1 == u2:
            return True

    # 3. High title token overlap (covers minor wording, punctuation, or filler word additions)
    if t1 and t2:
        tokens1 = set(t1.split())
        tokens2 = set(t2.split())
        if tokens1 and tokens2:
            intersection = tokens1 & tokens2
            # Subset match (e.g. "Software Engineer II - Mobile iOS" vs "Software Engineer II")
            if (tokens1.issubset(tokens2) or tokens2.issubset(tokens1)) and len(intersection) >= 2:
                return True
            # High Jaccard similarity (>= 0.6)
            jaccard = len(intersection) / len(tokens1 | tokens2)
            if jaccard >= 0.6 and len(intersection) >= 2:
                return True

    # 4. Fallback: exact raw item fingerprint match
    return extract_item_fingerprint(item1) == extract_item_fingerprint(item2)


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
            link = normalize_url(val)
            break

    title = ""
    for k in ["title", "name", "heading", "event"]:
        val = item.get(k)
        if val and isinstance(val, str) and val.strip():
            title = normalize_title(val)
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


def diff_and_annotate_results(
    prev_raw_result: Any,
    new_raw_result: str,
    prev_status: Optional[str] = None,
) -> Tuple[str, bool, int]:
    """
    Compares newly extracted result items against previous run results:
    - First run detection:
      If prev_status is not 'SUCCESS' (e.g. None or 'Pending'), OR if prev_raw_result is empty:
      This is the first run / initial baseline.
      Items are saved as baseline (is_new = False), has_new_items = False, new_items_count = 0.
      No notifications will be dispatched.
    - Subsequent runs (where prev_status == 'SUCCESS' and prev_raw_result exists):
      Each new item is compared against previous run items using is_same_item().
      Items matching any previously seen item are marked is_new = False.
      Items not matching any previously seen item are marked is_new = True.
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

    # Determine if this is the first run / baseline:
    # 1. If prev_status is provided and is not SUCCESS (e.g. None, Pending), it is a first run.
    # 2. If prev_raw_result is missing or empty, it is a first run.
    is_first_run = (
        (prev_status is not None and prev_status != "SUCCESS")
        or not prev_raw_result
        or not str(prev_raw_result).strip()
    )

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
        # Subsequent run: compare with previous run's items using robust matching
        prev_items = parse_result_items(prev_raw_result)

        if not prev_items:
            # Previous result had no items; treat current items as baseline
            for item in items:
                if isinstance(item, dict):
                    item["is_new"] = False
            has_new_items = False
            new_items_count = 0
        else:
            for item in items:
                if isinstance(item, dict):
                    already_seen = any(is_same_item(item, p) for p in prev_items)
                    if not already_seen:
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
