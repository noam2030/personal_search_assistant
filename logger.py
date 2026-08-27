from datetime import datetime

DEBUG_FILE = "debug_last_run.log"


def write_debug_log(
    url: str,
    goal: str,
    raw_html: str = "",
    cleaned_text: str = "",
    result: str = "",
    error: str | None = None,
):
    """
    Writes execution debug details to debug_last_run.log on every run,
    overwriting the previous run's log file. Includes complete raw HTML,
    cleaned text, and AI extraction results.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(DEBUG_FILE, "w", encoding="utf-8") as f:
        f.write("==================================================\n")
        f.write("  PERSONAL SEARCH ASSISTANT - LAST RUN DEBUG LOG  \n")
        f.write("==================================================\n")
        f.write(f"Timestamp : {timestamp}\n")
        f.write(f"Target URL: {url}\n")
        f.write(f"Goal      : {goal}\n")
        f.write(f"Status    : {'FAILED' if error else 'SUCCESS'}\n\n")

        if error:
            f.write("--------------------------------------------------\n")
            f.write(" ERROR DETAILS\n")
            f.write("--------------------------------------------------\n")
            f.write(f"{error}\n\n")

        f.write("--------------------------------------------------\n")
        f.write(" STEP 1: RAW HTML CONTENT\n")
        f.write("--------------------------------------------------\n")
        if raw_html:
            f.write(f"Raw HTML Character Count: {len(raw_html)}\n\n")
            f.write(raw_html)
        else:
            f.write("[No raw HTML content fetched]\n")
        f.write("\n\n")

        f.write("--------------------------------------------------\n")
        f.write(" STEP 2: CLEANED TEXT CONTENT\n")
        f.write("--------------------------------------------------\n")
        if cleaned_text:
            f.write(f"Cleaned Text Character Count: {len(cleaned_text)}\n\n")
            f.write(cleaned_text)
        else:
            f.write("[No cleaned text content generated]\n")
        f.write("\n\n")

        f.write("--------------------------------------------------\n")
        f.write(" STEP 3: GEMINI AI EXTRACTION RESULT\n")
        f.write("--------------------------------------------------\n")
        f.write(result if result else "[No extraction result generated]")
        f.write("\n")
