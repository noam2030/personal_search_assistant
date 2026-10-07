import os
import json
import httpx
from typing import List, Dict, Any, Optional


from backend.differ import has_task_new_items


def format_telegram_message(user_id: str, results: List[Dict[str, Any]]) -> str:
    """
    Formats a list of task execution results into clean Markdown for Telegram messaging,
    highlighting newly discovered items with 🆕 tags.
    """
    lines = [
        "🔍 *Personal Search Assistant*",
        f"✨ *New items discovered for user* `{user_id}`",
        "----------------------------------------",
    ]

    if not results:
        lines.append("No new items were discovered.")
        return "\n".join(lines)

    task_sections_added = 0

    for task in results:
        name = task.get("name", "Task")
        status = task.get("last_status", "UNKNOWN")
        icon = "✅" if status == "SUCCESS" else "❌"

        if status == "FAILED":
            lines.append(f"\n{icon} *{name}* (ID: `{task.get('id')}`)")
            err = task.get("last_error") or "Unknown error"
            lines.append(f"└ Error: `{err}`")
            task_sections_added += 1
            continue

        raw_result = task.get("last_result")
        if not raw_result:
            continue

        try:
            clean_raw = str(raw_result).replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean_raw)
            items = []
            if isinstance(parsed, list):
                items = parsed
            elif isinstance(parsed, dict):
                for key in ["items", "results", "events", "data"]:
                    if isinstance(parsed.get(key), list):
                        items = parsed[key]
                        break

            # Filter strictly to new items
            new_items = [i for i in items if isinstance(i, dict) and i.get("is_new") is True]
            if not new_items:
                continue

            lines.append(f"\n{icon} *{name}* (ID: `{task.get('id')}`)")
            lines.append(f"└ Found *{len(new_items)} new item(s)*:")

            # Show top 5 items
            for idx, item in enumerate(new_items[:5], 1):
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

                    badge = "🆕 "
                    if link:
                        lines.append(f"   {badge}[{title}]({link})")
                    else:
                        lines.append(f"   {badge}{title}")
                else:
                    lines.append(f"   • {item}")

            if len(new_items) > 5:
                lines.append(f"   _...and {len(new_items) - 5} more items_")

            task_sections_added += 1

        except Exception:
            continue

    if task_sections_added == 0:
        lines.append("No new items were discovered.")

    return "\n".join(lines)


def send_telegram_message(text: str, chat_id: Optional[str] = None) -> bool:
    """
    Sends raw text message to Telegram Bot using configured TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    target_chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not target_chat_id:
        print("[Notifier] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured. Skipping Telegram message.")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": target_chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        if response.status_code == 200:
            print(f"✓ Telegram message sent successfully to chat_id '{target_chat_id}'.")
            return True
        else:
            print(f"✗ Failed to send Telegram message (HTTP {response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"✗ Telegram message exception: {e}")
        return False


def send_telegram_notification(user_id: str, results: List[Dict[str, Any]]) -> bool:
    """
    Sends execution summary message to Telegram Bot ONLY if new items were discovered.
    If all tasks have unchanged items (or first baseline run), skips notification.
    """
    tasks_with_new = [t for t in results if has_task_new_items(t)]
    if not tasks_with_new:
        print(f"[Notifier] No new items discovered for user '{user_id}'. Skipping Telegram notification.")
        return False

    message_text = format_telegram_message(user_id, tasks_with_new)
    if "No new items were discovered." in message_text:
        print(f"[Notifier] No new items discovered for user '{user_id}'. Skipping Telegram notification.")
        return False
    return send_telegram_message(text=message_text)
