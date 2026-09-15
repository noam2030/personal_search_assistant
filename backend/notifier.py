import os
import json
import httpx
from typing import List, Dict, Any, Optional

from backend import db
from backend.controller import run_task_by_id, run_user_tasks


def format_telegram_message(user_id: str, results: List[Dict[str, Any]]) -> str:
    """
    Formats a list of task execution results into clean Markdown for Telegram messaging.
    """
    lines = [
        "🔍 *Personal Search Assistant*",
        f"📅 Run Summary for user `{user_id}`",
        "----------------------------------------",
    ]

    if not results:
        lines.append("No active tasks were executed.")
        return "\n".join(lines)

    for task in results:
        name = task.get("name", "Task")
        status = task.get("last_status", "UNKNOWN")
        icon = "✅" if status == "SUCCESS" else "❌"

        lines.append(f"\n{icon} *{name}* (ID: `{task.get('id')}`) ")

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
    Sends execution summary message to Telegram Bot reusing send_telegram_message.
    """
    message_text = format_telegram_message(user_id, results)
    return send_telegram_message(text=message_text)


# =============================================================================
# Interactive Telegram Bot Commands & Update Dispatcher
# =============================================================================

def cmd_help_menu() -> str:
    return (
        "🤖 *Personal Search Assistant Bot*\n\n"
        "Here are the available commands:\n"
        "• `/tasks` or `/list` - List your active search tasks\n"
        "• `/add <description>` - Add a new search task\n"
        "• `/run <id>` - Run execution for task with ID `<id>`\n"
        "• `/runall` - Run execution for all active tasks\n"
        "• `/delete <id>` - Delete task with ID `<id>`\n"
        "• `/help` - Show this menu\n\n"
        "💡 *Tip:* Send any text message directly (without `/`) to create a new task!"
    )


def cmd_list_tasks(user_id: str) -> str:
    tasks = db.list_tasks(user_id=user_id)
    if not tasks:
        return f"📋 *Tasks for user `{user_id}`*\n\nNo active tasks found. Send `/add <description>` to create one!"

    lines = [f"📋 *Tasks for user `{user_id}` ({len(tasks)})*", "----------------------------------------"]
    for t in tasks:
        task_id = t["id"]
        name = t.get("name") or "Task"
        status = t.get("last_status") or "Pending"
        desc = t.get("task_description", "")
        status_icon = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "⏳"

        lines.append(f"• *[ID: {task_id}]* {status_icon} *{name}*")
        lines.append(f"  _{desc}_")

    lines.append("\n_Use `/run <id>` to execute a specific task, or `/runall` to run all tasks._")
    return "\n".join(lines)


def cmd_add_task(user_id: str, task_description: str) -> str:
    if not task_description.strip():
        return "❌ Please provide a task description. Example: `/add find me jobs in Tel Aviv Java backend`"

    new_task = db.add_task(user_id=user_id, name="", task_description=task_description.strip())
    return (
        f"✅ *New Task Created!*\n\n"
        f"• *ID:* `{new_task['id']}`\n"
        f"• *Description:* {new_task['task_description']}\n\n"
        f"Use `/run {new_task['id']}` to execute it now!"
    )


def cmd_run_task(task_id_str: str) -> str:
    if not task_id_str.isdigit():
        return "❌ Invalid task ID. Please specify a numeric task ID. Example: `/run 5`"

    task_id = int(task_id_str)
    task = db.get_task(task_id)
    if not task:
        return f"❌ Task with ID `{task_id}` not found."

    try:
        updated_task = run_task_by_id(task_id=task_id)
        return format_telegram_message(user_id=updated_task["user_id"], results=[updated_task])
    except Exception as e:
        return f"❌ Task `{task_id}` execution failed: `{str(e)}`"


def cmd_run_all_tasks(user_id: str) -> str:
    results = run_user_tasks(user_id=user_id)
    return format_telegram_message(user_id=user_id, results=results)


def cmd_delete_task(user_id: str, task_id_str: str) -> str:
    if not task_id_str.isdigit():
        return "❌ Invalid task ID. Example: `/delete 5`"

    task_id = int(task_id_str)
    task = db.get_task(task_id)
    if not task:
        return f"❌ Task with ID `{task_id}` not found."

    success = db.delete_task(task_id=task_id, user_id=user_id)
    if success:
        return f"🗑️ Task `[ID: {task_id}]` (*{task.get('name', 'Task')}*) deleted successfully."
    return f"❌ Failed to delete task `{task_id}`."


def handle_telegram_update(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Stage 1 Telegram Webhook Handler:
    Extracts text and chat_id from incoming update, prints text to console logs,
    and sends a simple confirmation reply back to Telegram.
    """
    message = payload.get("message") or payload.get("edited_message")
    if not message or "text" not in message:
        return {"status": "ignored", "reason": "No text message in update"}

    chat_id = str(message.get("chat", {}).get("id"))
    text = message.get("text", "").strip()

    # Stage 1: Print received message details to backend logs
    print(f"\n========================================")
    print(f"[Telegram Webhook Stage 1]")
    print(f"Chat ID: {chat_id}")
    print(f"Message Text: {text}")
    print(f"========================================\n")

    # Security check: verify incoming chat_id matches TELEGRAM_CHAT_ID (if configured)
    allowed_chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if allowed_chat_id and chat_id != str(allowed_chat_id):
        print(f"[Webhook] Rejected unauthorized update from chat_id: {chat_id}")
        return {"status": "rejected", "reason": "Unauthorized chat_id"}

    # Stage 1: Echo reply back to Telegram
    reply_text = f"📩 *Message Received (Stage 1)*\n\nText: `{text}`"
    send_telegram_message(text=reply_text, chat_id=chat_id)

    return {"status": "ok", "chat_id": chat_id, "text": text}
