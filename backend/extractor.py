import os
import re
import time
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file if available
load_dotenv()


def extract_content(goal: str, cleaned_text: str | None = None) -> str:
    """
    Passes the goal (and optional cleaned webpage text) to Gemini API.
    If no webpage text is provided, Gemini executes live Google Search Grounding.
    Includes retry logic and friendly network error handling.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it in your environment or in a .env file."
        )

    client = genai.Client(api_key=api_key)

    if cleaned_text:
        prompt = (
            f"You are an AI Personal Search Assistant.\n"
            f"Goal: {goal}\n\n"
            f"Below is the cleaned text content from the target webpage:\n"
            f"---------------------\n"
            f"{cleaned_text[:30000]}\n"
            f"---------------------\n\n"
            f"Task:\n"
            f"1. Generate a concise 3-5 word task title summarizing the goal (e.g. 'Tel Aviv Java Backend Jobs').\n"
            f"2. Extract all items matching the goal.\n"
            f"3. Return ONLY a valid JSON object strictly matching this schema:\n"
            f"{{\n"
            f'  "task_title": "Short Descriptive Title",\n'
            f'  "items": [\n'
            f'    {{\n'
            f'      "title": "Item Title",\n'
            f'      "link": "https://...",\n'
            f'      "description": "Details",\n'
            f'      "location": "Location if applicable"\n'
            f'    }}\n'
            f'  ]\n'
            f"}}\n"
        )
        return _call_gemini_with_retry(client, prompt)
    else:
        # Pure natural language prompt -> Enable Google Search Grounding
        prompt = (
            f"You are an AI Personal Search Assistant equipped with Google Search.\n"
            f"User Goal: {goal}\n\n"
            f"Task:\n"
            f"1. Perform a web search to find live information matching the user's goal.\n"
            f"2. Generate a concise 3-5 word task title summarizing the goal (e.g. 'Tel Aviv Java Backend Jobs').\n"
            f"3. Extract matching items with titles, links, and key details.\n"
            f"4. Return ONLY a valid JSON object strictly matching this schema:\n"
            f"{{\n"
            f'  "task_title": "Short Descriptive Title",\n'
            f'  "items": [\n'
            f'    {{\n'
            f'      "title": "Item Title",\n'
            f'      "link": "https://...",\n'
            f'      "description": "Details",\n'
            f'      "location": "Location if applicable"\n'
            f'    }}\n'
            f'  ]\n'
            f"}}\n"
        )
        try:
            return _call_gemini_with_retry(client, prompt, config={"tools": [{"google_search": {}}]})
        except Exception as err:
            print(f"[Warning] Grounding fallback attempt: {err}")
            return _call_gemini_with_retry(client, prompt)


def _call_gemini_with_retry(client, prompt: str, config=None, retries: int = 3) -> str:
    """Executes generate_content with retries and clean DNS/network error handling."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            if config:
                res = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt,
                    config=config,
                )
            else:
                res = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt,
                )
            return res.text
        except Exception as e:
            last_err = e
            print(f"[Attempt {attempt}/{retries}] Gemini API call failed: {e}")
            if attempt < retries:
                time.sleep(1)

    error_str = str(last_err)
    if "nodename nor servname provided" in error_str or "getaddrinfo failed" in error_str:
        raise RuntimeError(
            "Internet/DNS connection unavailable. Please check your internet connection or Wi-Fi and try running the task again."
        ) from last_err

    raise RuntimeError(f"Gemini API request failed after {retries} attempts: {last_err}") from last_err
