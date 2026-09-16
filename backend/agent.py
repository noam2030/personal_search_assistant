import os
import json
import time
from typing import Dict, Any, List

from google import genai
from backend import db
from backend.controller import run_task_by_id, run_user_tasks
from backend.notifier import format_telegram_message


def process_telegram_intent(user_id: str, message_text: str) -> str:
    """
    Intelligent AI Agent Intent Dispatcher:
    Uses Gemini AI to understand natural language intent from a Telegram user message,
    maps intent to backend task actions (CREATE_TASK, LIST_TASKS, RUN_TASK, RUN_ALL_TASKS, DELETE_TASK, REPLY, NO_ACTION),
    executes the appropriate backend controller/DB function, and returns formatted Markdown reply text.
    """
    clean_text = message_text.strip()
    if not clean_text:
        return "Please send a message or task description!"

    tasks = db.list_tasks(user_id=user_id)
    tasks_context = [
        {
            "id": t["id"],
            "name": t.get("name", "Task"),
            "task_description": t.get("task_description", ""),
            "last_status": t.get("last_status", "Pending"),
        }
        for t in tasks
    ]

    # AI Intent Classification via Gemini
    ai_decision = _classify_intent_with_gemini(message_text=clean_text, tasks_context=tasks_context)

    action = ai_decision.get("action", "NO_ACTION")

    if action == "LIST_TASKS":
        return _format_task_list_reply(user_id=user_id, tasks=tasks)

    elif action == "CREATE_TASK":
        task_desc = ai_decision.get("task_description") or clean_text
        new_task = db.add_task(user_id=user_id, name="", task_description=task_desc)
        return (
            f"✅ *New Task Created!*\n\n"
            f"• *ID:* `{new_task['id']}`\n"
            f"• *Description:* {new_task['task_description']}\n\n"
            f"I will monitor this for you. You can ask me to run it anytime!"
        )

    elif action == "RUN_TASK":
        task_id = ai_decision.get("task_id")
        if not task_id:
            # Fallback: attempt running first task if single task exists
            if len(tasks) == 1:
                task_id = tasks[0]["id"]
            else:
                return _format_task_list_reply(user_id=user_id, tasks=tasks)

        target_task = db.get_task(int(task_id))
        if not target_task:
            return f"❌ Task with ID `{task_id}` not found."

        try:
            updated_task = run_task_by_id(task_id=int(task_id))
            return format_telegram_message(user_id=user_id, results=[updated_task])
        except Exception as e:
            return f"❌ Task execution failed for ID `{task_id}`: `{str(e)}`"

    elif action == "RUN_ALL_TASKS":
        if not tasks:
            return f"📋 No tasks found for user `{user_id}`. Tell me what you'd like to search for to create a task!"
        results = run_user_tasks(user_id=user_id)
        return format_telegram_message(user_id=user_id, results=results)

    elif action == "DELETE_TASK":
        task_id = ai_decision.get("task_id")
        if not task_id:
            return "❌ Please specify which task ID to delete (e.g. 'delete task 3')."

        target_task = db.get_task(int(task_id))
        if not target_task:
            return f"❌ Task with ID `{task_id}` not found."

        success = db.delete_task(task_id=int(task_id), user_id=user_id)
        if success:
            return f"🗑️ Task `[ID: {task_id}]` (*{target_task.get('name', 'Task')}*) deleted successfully."
        return f"❌ Failed to delete task `{task_id}`."

    elif action == "REPLY":
        return ai_decision.get("text") or "I am your AI Personal Search Assistant. How can I help you today?"

    elif action == "NO_ACTION":
        return ai_decision.get("text") or "No action taken."

    # Default fallback when no action matches
    return ai_decision.get("text") or "No action taken."


def _classify_intent_with_gemini(message_text: str, tasks_context: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calls Gemini API to perform natural language intent classification against user message & active task context.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[Warning] GEMINI_API_KEY not set. Cannot perform AI intent classification.")
        return {"action": "NO_ACTION", "text": "GEMINI_API_KEY not configured."}

    try:
        client = genai.Client(api_key=api_key)
        prompt = (
            f"You are an AI Personal Search Assistant Intent Classifier.\n"
            f"Your job is to understand the user's natural language message and map it to the correct action.\n\n"
            f"User's Active Tasks Context:\n"
            f"{json.dumps(tasks_context, indent=2)}\n\n"
            f"User Message: {message_text}\n\n"
            f"Allowed Actions:\n"
            f'1. LIST_TASKS: User asks to see, view, or list their current tasks (e.g. "show tasks", "/list", "what tasks do I have?").\n'
            f'2. CREATE_TASK: User wants to monitor, search, or track new information (e.g. "find me jobs in Tel Aviv", "check flight prices to Paris").\n'
            f'   Return: {{"action": "CREATE_TASK", "task_description": "extracted goal description"}}\n'
            f'3. RUN_TASK: User asks to execute/run a specific task (e.g. "run task 5", "check my Tel Aviv job search"). Match task_id from context if available.\n'
            f'   Return: {{"action": "RUN_TASK", "task_id": 5}}\n'
            f'4. RUN_ALL_TASKS: User asks to run/execute all tasks at once (e.g. "run all tasks", "check everything").\n'
            f'   Return: {{"action": "RUN_ALL_TASKS"}}\n'
            f'5. DELETE_TASK: User asks to delete/remove a task (e.g. "delete task 3", "remove my job alert"). Match task_id from context if available.\n'
            f'   Return: {{"action": "DELETE_TASK", "task_id": 3}}\n'
            f'6. REPLY: General greeting, conversational question, or help request (e.g. "hello", "who are you?", "/help").\n'
            f'   Return: {{"action": "REPLY", "text": "friendly response"}}\n'
            f'7. NO_ACTION: Message requires no action or cannot be mapped to any specific task action.\n'
            f'   Return: {{"action": "NO_ACTION", "text": "No action taken."}}\n\n'
            f"Respond ONLY with a valid JSON object."
        )

        res = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )

        clean_raw = res.text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_raw)
        if isinstance(parsed, dict) and "action" in parsed:
            return parsed
    except Exception as e:
        print(f"[Warning] Gemini intent classification error: {e}")

    return {"action": "NO_ACTION", "text": "Failed to classify intent."}


def _format_task_list_reply(user_id: str, tasks: List[Dict[str, Any]]) -> str:
    if not tasks:
        return f"📋 *Tasks for user `{user_id}`*\n\nNo active tasks found. Send me any search request (e.g. *'Find me jobs in Tel Aviv'*) to create one!"

    lines = [f"📋 *Tasks for user `{user_id}` ({len(tasks)})*", "----------------------------------------"]
    for t in tasks:
        task_id = t["id"]
        name = t.get("name") or "Task"
        status = t.get("last_status") or "Pending"
        desc = t.get("task_description", "")
        status_icon = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "⏳"

        lines.append(f"• *[ID: {task_id}]* {status_icon} *{name}*")
        lines.append(f"  _{desc}_")

    lines.append("\n_You can tell me to 'Run task <id>', 'Run all tasks', or send a new search request!_")
    return "\n".join(lines)
