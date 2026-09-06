from datetime import datetime

DEBUG_FILE = "debug_last_run.log"


def write_debug_log(
    task_description: str,
    raw_html: str = "",
    cleaned_text: str = "",
    result: str = "",
    error: str | None = None,
):
    """
    Writes execution debug details to debug_last_run.log on every run,
    overwriting the previous run's log file. Includes complete prompt,
    execution trace, and AI extraction results.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(DEBUG_FILE, "w", encoding="utf-8") as f:
        f.write("==================================================\n")
        f.write("  PERSONAL SEARCH ASSISTANT - LAST RUN DEBUG LOG  \n")
        f.write("==================================================\n")
        f.write(f"Timestamp   : {timestamp}\n")
        f.write(f"Description : {task_description}\n")
        f.write(f"Status      : {'FAILED' if error else 'SUCCESS'}\n\n")

        if error:
            f.write("--------------------------------------------------\n")
            f.write(" ERROR DETAILS\n")
            f.write("--------------------------------------------------\n")
            f.write(f"{error}\n\n")

        f.write("--------------------------------------------------\n")
        f.write(" STEP 1: GEMINI AI EXTRACTION RESULT\n")
        f.write("--------------------------------------------------\n")
        f.write(result if result else "[No extraction result generated]")
        f.write("\n")
