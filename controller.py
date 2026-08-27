from fetcher import fetch_html
from cleaner import clean_html
from extractor import extract_content
from logger import write_debug_log


def run_task(url: str, goal: str) -> str:
    """
    Orchestrates the entire extraction task pipeline:
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
        # Immediately write raw HTML to debug log as soon as it is fetched
        write_debug_log(url, goal, raw_html=raw_html, cleaned_text=cleaned_text, result=result)
    except Exception as e:
        error_msg = f"Error fetching URL '{url}': {e}"
        write_debug_log(url, goal, raw_html=raw_html, cleaned_text=cleaned_text, result=result, error=error_msg)
        raise RuntimeError(error_msg) from e

    print("[2/3] Cleaning HTML content ...")
    cleaned_text = clean_html(raw_html)
    # Update debug log with cleaned text
    write_debug_log(url, goal, raw_html=raw_html, cleaned_text=cleaned_text, result=result)

    if not cleaned_text:
        error_msg = f"Cleaned webpage content is empty for URL '{url}'."
        write_debug_log(url, goal, raw_html=raw_html, cleaned_text=cleaned_text, result=result, error=error_msg)
        raise ValueError(error_msg)

    print(f"[3/3] Extracting information with Gemini AI for goal: '{goal}' ...\n")
    try:
        result = extract_content(cleaned_text, goal)
        # Update debug log with final extraction result
        write_debug_log(url, goal, raw_html=raw_html, cleaned_text=cleaned_text, result=result)
        return result
    except Exception as e:
        error_msg = f"Error during AI extraction: {e}"
        write_debug_log(url, goal, raw_html=raw_html, cleaned_text=cleaned_text, result=result, error=error_msg)
        raise RuntimeError(error_msg) from e
