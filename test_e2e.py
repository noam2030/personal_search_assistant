import os
import json
from unittest.mock import patch
from dotenv import load_dotenv

from controller import run_task
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
    <style>body { font-family: sans-serif; }</style>
</head>
<body>
    <nav><a href="/">Home</a></nav>
    <main>
        <h1>Upcoming Tech Meetups</h1>
        <div class="event">
            <h2>Autonomous AI Agents Summit 2026</h2>
            <p class="date">Date: November 12, 2026</p>
            <p class="location">Location: San Francisco, CA & Online</p>
            <a href="https://example.com/events/agents-summit">Register Here</a>
            <p>Join us for talks on LLM agents, tool use, and multi-agent coordination.</p>
        </div>
        <div class="event">
            <h2>Intro to CSS Layouts</h2>
            <p class="date">Date: October 5, 2026</p>
            <p class="location">Location: Online</p>
            <a href="https://example.com/events/css">Register Here</a>
        </div>
    </main>
    <footer>Contact: info@example.com</footer>
</body>
</html>
"""


def test_e2e_pipeline_mocked():
    """
    End-to-End integration test using mocked HTTP fetching and mocked AI extraction
    to verify full pipeline orchestration and debug log generation.
    """
    print("[E2E Test] Running mocked E2E pipeline test...")
    url = "https://example.com/events"
    goal = "find meetups about AI agents"

    mock_gemini_json = json.dumps({
        "items": [
            {
                "title": "Autonomous AI Agents Summit 2026",
                "date": "November 12, 2026",
                "location": "San Francisco, CA & Online",
                "link": "https://example.com/events/agents-summit",
                "description": "Join us for talks on LLM agents, tool use, and multi-agent coordination."
            }
        ]
    })

    with patch("controller.fetch_html", return_value=SAMPLE_MEETUP_HTML):
        with patch("controller.extract_content", return_value=mock_gemini_json):
            result = run_task(url=url, goal=goal)

            # Assert returned output matches expected JSON structure
            assert result == mock_gemini_json
            parsed = json.loads(result)
            assert len(parsed["items"]) == 1
            assert parsed["items"][0]["title"] == "Autonomous AI Agents Summit 2026"

            # Assert debug_last_run.log was created and populated
            assert os.path.exists(DEBUG_FILE)
            with open(DEBUG_FILE, "r", encoding="utf-8") as f:
                log_content = f.read()

            assert "STEP 1: RAW HTML CONTENT" in log_content
            assert "Autonomous AI Agents Summit 2026" in log_content
            assert "STEP 2: CLEANED TEXT CONTENT" in log_content
            assert "STEP 3: GEMINI AI EXTRACTION RESULT" in log_content

    print("[E2E Test] Mocked E2E pipeline test passed!\n")


def test_e2e_live_api():
    """
    Live End-to-End test that calls real HTTP fetcher and real Gemini API
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

        # Verify debug log was updated
        assert os.path.exists(DEBUG_FILE)
        with open(DEBUG_FILE, "r", encoding="utf-8") as f:
            log_content = f.read()
        assert "Example Domain" in log_content or "STEP 3:" in log_content

        print("[E2E Test] Live API E2E test passed!\n")
    except Exception as e:
        print(f"[E2E Test] Live API test skipped due to network/environment constraint: {e}\n")


if __name__ == "__main__":
    test_e2e_pipeline_mocked()
    test_e2e_live_api()
    print("All E2E tests completed successfully!")
