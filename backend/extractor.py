import os
import re
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file if available
load_dotenv()


def extract_content(goal: str, cleaned_text: str | None = None) -> str:
    """
    Passes the goal (and optional cleaned webpage text) to Gemini API.
    If no webpage text is provided, Gemini executes live Google Search Grounding.
    Also returns a concise 3-5 word task_title in the JSON response.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it in your environment or in a .env file."
        )

    client = genai.Client(api_key=api_key)

    # Detect if the goal prompt contains an explicit URL
    url_match = re.search(r'https?://[^\s]+', goal)
    explicit_url = url_match.group(0) if url_match else None

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
            f'      "location": "Location if applicable",\n'
            f'      "price": "Price/Date if applicable"\n'
            f'    }}\n'
            f'  ]\n'
            f"}}\n"
        )
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
    else:
        # Pure natural language prompt -> Enable Google Search Grounding
        prompt = (
            f"You are an AI Personal Search Assistant equipped with Google Search.\n"
            f"User Goal: {goal}\n\n"
            f"Task:\n"
            f"1. Perform a web search to find live information matching the user's goal.\n"
            f"2. Generate a concise 3-5 word task title summarizing the goal.\n"
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
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
                config={"tools": [{"google_search": {}}]},
            )
        except Exception as err:
            # Fallback without search tool if grounding config is restricted in specific region
            print(f"[Warning] Grounding fallback: {err}")
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )

    return response.text
