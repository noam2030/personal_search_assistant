import os
import json
import httpx
from typing import List, Dict, Any


def format_telegram_message(user_id: str, results: List[Dict[str, Any]]) -> str:
    """
    Formats a list of task execution results into clean Markdown for Telegram messaging.
    """
    lines = [
        "🔍 *Personal Search Assistant*",
        f"📅 Daily Run Summary for user `{user_id}`",
        "----------------------------------------",
    ]

    if not results:
        lines.append("No active tasks were executed.")
        return "\n".join(lines)

    for task in results:
        name = task.get("name", "Task")
        status = task.get("last_status", "UNKNOWN")
        icon = "✅" if status == "SUCCESS" else "❌"

        lines.append(f"\n{icon} *{name}*")

        if status == "FAILED":
            err = task.get("last_error") or "Unknown error"
            lines.append(f"└ Error: `{err}`")
            continue

        raw_result = task.get("last_result")
        if not raw_result:
            lines.append("└ _No results recorded_")
            continue

        try:
            clean_raw = raw_result.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean_raw)
            items = []
            if isinstance(parsed, list):
                items = parsed
            elif isinstance(parsed, dict):
                for key in ["items", "results", "events", "data"]:
                    if isinstance(parsed.get(key), list):
                        items = parsed[key]
                        break

            lines.append(f"└ Found *{len(items)} item(s)*")

            # Show top 3 items
            for idx, item in enumerate(items[:3], 1):
                if isinstance(item, dict):
                    title_key = next(
                        (k for k in item.keys() if any(w in k.lower() for w in ["title", "name", "heading"])),
                        list(item.keys())[0] if item else "Item",
                    )
                    title = str(item.get(title_key, f"Item {idx}"))
                    link_key = next(
                        (k for k in item.keys() if any(w in k.lower() for w in ["link", "url", "href", "website"])),
                        None,
                    )
                    link = str(item[link_key]) if link_key and item.get(link_key) else None

                    if link:
                        lines.append(f"   • [{title}]({link})")
                    else:
                        lines.append(f"   • {title}")
                else:
                    lines.append(f"   • {item}")

            if len(items) > 3:
                lines.append(f"   _...and {len(items) - 3} more items_")

        except Exception:
            lines.append("└ _Result format could not be parsed_")

    return "\n".join(lines)


def send_telegram_notification(user_id: str, results: List[Dict[str, Any]]) -> bool:
    """
    Sends execution summary message to Telegram Bot if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are configured.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        print("[Notifier] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured. Skipping Telegram notification.")
        return False

    message_text = format_telegram_message(user_id, results)
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message_text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        if response.status_code == 200:
            print(f"✓ Telegram notification sent successfully to chat_id '{chat_id}'.")
            return True
        else:
            print(f"✗ Failed to send Telegram notification (HTTP {response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"✗ Telegram notification exception: {e}")
        return False
