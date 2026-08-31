import os
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env file if available
load_dotenv()


def extract_content(cleaned_text: str, goal: str) -> str:
    """
    Passes the cleaned text and goal to Gemini API to extract matching structured content.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it in your environment or in a .env file."
        )

    client = genai.Client(api_key=api_key)

    prompt = (
        f"You are a web search assistant AI agent.\n"
        f"Goal: {goal}\n\n"
        f"Below is the cleaned text content from the target webpage:\n"
        f"---------------------\n"
        f"{cleaned_text[:30000]}\n"  # Limit context length safely
        f"---------------------\n\n"
        f"Task:\n"
        f"1. Extract all items/information matching the goal above.\n"
        f"2. Format the response cleanly in structured JSON (with fields like title, date, location, link, description, price as appropriate).\n"
        f"3. If no matching items are found, return a JSON object with 'items': [] and a brief 'reason'."
    )

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
    )

    return response.text
