import os
import time
import socket
import asyncio
import concurrent.futures
from dotenv import load_dotenv

from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.adk.tools.google_search_tool import google_search
from backend.agent.skills import format_skills_for_prompt

# Force IPv4 socket resolution on macOS to avoid IPv6 [Errno 8] DNS lookup errors
old_getaddrinfo = socket.getaddrinfo
def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    try:
        return old_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    except Exception:
        return old_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = ipv4_getaddrinfo

# Load environment variables from .env file if available
load_dotenv()


def _ensure_api_key() -> str:
    """Ensures Gemini / Google API key is configured and exported for Google ADK."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set it in your environment or in a .env file."
        )
    if not os.getenv("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = api_key
    return api_key


EXTRACT_INSTRUCTION = (
    "You are an AI Personal Search Assistant equipped with Google Search.\n"
    "Task:\n"
    "1. Understand the user's intent (e.g. finding jobs, price/room monitoring, item discovery).\n"
    "2. Perform a web search using the google_search tool to find live information matching the user's request.\n"
    "3. Generate a concise 3-5 word task title summarizing the goal (e.g. 'Tel Aviv Java Backend Jobs').\n"
    "4. Extract matching items with titles, links, and key details.\n"
    "5. Return ONLY a valid JSON object strictly matching this schema:\n"
    "{\n"
    '  "task_title": "Short Descriptive Title",\n'
    '  "items": [\n'
    "    {\n"
    '      "title": "Item Title",\n'
    '      "link": "https://...",\n'
    '      "description": "Details",\n'
    '      "location": "Location if applicable",\n'
    '      "website": "Source website or domain (e.g. geektime.co.il)"\n'
    "    }\n"
    "  ]\n"
    "}\n"
)


def _get_combined_instruction() -> str:
    """Returns base instruction augmented with any active workspace skills."""
    skills_context = format_skills_for_prompt()
    if not skills_context:
        return EXTRACT_INSTRUCTION
    return (
        f"{EXTRACT_INSTRUCTION}\n\n"
        f"{skills_context}\n\n"
        "IMPORTANT SEARCH DIRECTIVE: When a user query matches any domain covered by the Workspace Skills above, "
        "you MUST strictly prioritize and restrict your search sources according to the skill instructions "
        "(e.g. searching within geektime.co.il for tech events using the google_search tool)."
    )


# Google ADK Search & Extraction Agent
extract_agent = Agent(
    name="extract_content_agent",
    model="gemini-3.6-flash",
    description="Understands user search intent, executes Google Search via ADK, and extracts structured items.",
    instruction=_get_combined_instruction(),
    tools=[google_search],
)

# Fallback Google ADK Agent without search tool (used when search grounding is unavailable)
extract_agent_fallback = Agent(
    name="extract_content_agent_fallback",
    model="gemini-3.6-flash",
    description="Fallback search extraction agent without live search grounding.",
    instruction=_get_combined_instruction(),
)


def _run_adk_agent_sync(agent: Agent, prompt: str) -> str:
    """Executes an ADK agent synchronously, handling active or nested asyncio event loops."""
    async def _run() -> str:
        runner = InMemoryRunner(agent=agent)
        events = await runner.run_debug(prompt, quiet=True)
        text_parts = []
        for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        text_parts.append(part.text)
        return "".join(text_parts).strip()

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(lambda: asyncio.run(_run())).result()
    else:
        return asyncio.run(_run())


def extract_content(task_description: str) -> str:
    """
    Passes the task_description to the Google ADK Agent equipped with Google Search tool.
    The ADK Agent executes live search/extraction and returns task_title + items as a JSON string.
    Workspace skills from .agents/skills/ are dynamically loaded and enforced.
    """
    _ensure_api_key()

    skills_context = format_skills_for_prompt()
    combined_instruction = _get_combined_instruction()
    extract_agent.instruction = combined_instruction
    extract_agent_fallback.instruction = combined_instruction

    prompt = f"User Natural Language Request: {task_description}"
    if skills_context:
        prompt += (
            f"\n\n{skills_context}\n\n"
            "MANDATORY REQUIREMENT: If the user request matches or relates to any of the skills above (e.g. finding tech events), "
            "you MUST strictly follow the skill guidelines. For example, for tech events, use the google_search tool to search "
            "within geektime.co.il (e.g. query 'site:geektime.co.il' or search Geektime event listings) and extract events from that website."
        )

    try:
        return _call_adk_with_retry(extract_agent, prompt)
    except Exception as err:
        print(f"[Warning] ADK Grounding fallback attempt: {err}")
        return _call_adk_with_retry(extract_agent_fallback, prompt)


def _call_adk_with_retry(agent: Agent, prompt: str, retries: int = 3) -> str:
    """Executes ADK agent with retries and clean DNS/network error handling."""
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            return _run_adk_agent_sync(agent, prompt)
        except Exception as e:
            last_err = e
            print(f"[Attempt {attempt}/{retries}] ADK Agent call failed: {e}")
            if attempt < retries:
                time.sleep(1)

    error_str = str(last_err)
    if "nodename nor servname provided" in error_str or "getaddrinfo failed" in error_str:
        raise RuntimeError(
            f"Network DNS lookup failed on local Mac ({last_err}). Please check your Wi-Fi or run the task again."
        ) from last_err

    raise RuntimeError(f"ADK Agent request failed after {retries} attempts: {last_err}") from last_err


def _call_gemini_with_retry(client, prompt: str, config=None, retries: int = 3) -> str:
    """Backwards-compatible wrapper redirecting to ADK execution."""
    agent = extract_agent if config else extract_agent_fallback
    return _call_adk_with_retry(agent, prompt, retries=retries)
