import argparse
import json
import sys
from backend.controller import run_task, run_user_tasks, run_task_by_id
from backend import db


def get_result_count(last_result: str | None) -> int | None:
    if not last_result:
        return None
    try:
        clean_raw = last_result.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_raw)
        if isinstance(parsed, list):
            return len(parsed)
        elif isinstance(parsed, dict):
            for key in ["items", "results", "events", "data"]:
                if isinstance(parsed.get(key), list):
                    return len(parsed[key])
        return 0
    except Exception:
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Personal Search Assistant Agent - Task Manager & AI Extractor"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: add-task
    add_parser = subparsers.add_parser("add-task", help="Add a new persistent task for a user")
    add_parser.add_argument("--user", type=str, required=True, help="User ID (e.g. 'noam')")
    add_parser.add_argument("--description", type=str, required=True, help="Task description / prompt")
    add_parser.add_argument("--name", type=str, help="Optional task name")

    # Command: list-tasks
    list_parser = subparsers.add_parser("list-tasks", help="List all persistent tasks for a user")
    list_parser.add_argument("--user", type=str, required=True, help="User ID (e.g. 'noam')")

    # Command: run-tasks
    run_tasks_parser = subparsers.add_parser("run-tasks", help="Run all persistent tasks for a user")
    run_tasks_parser.add_argument("--user", type=str, required=True, help="User ID (e.g. 'noam')")

    # Command: run-task-by-id
    run_task_id_parser = subparsers.add_parser("run-task-by-id", help="Run a single persistent task by task ID")
    run_task_id_parser.add_argument("--id", type=int, required=True, help="Task ID to execute")

    # Command: show-results
    show_parser = subparsers.add_parser("show-results", help="Show saved latest results for a user")
    show_parser.add_argument("--user", type=str, required=True, help="User ID (e.g. 'noam')")

    # Command: delete-task
    del_parser = subparsers.add_parser("delete-task", help="Delete a persistent task by ID")
    del_parser.add_argument("--user", type=str, required=True, help="User ID (e.g. 'noam')")
    del_parser.add_argument("--id", type=int, required=True, help="Task ID to delete")

    # Single-run option: --description
    parser.add_argument("--description", type=str, help="Task description (single-run mode)")

    args = parser.parse_args()

    # Handle subcommands
    if args.command == "add-task":
        initial_name = args.name or (args.description[:40] + ("..." if len(args.description) > 40 else ""))
        task = db.add_task(user_id=args.user, name=initial_name, task_description=args.description)
        print(f"✓ Task '{task['name']}' (ID: {task['id']}) created for user '{args.user}'.")

    elif args.command == "list-tasks":
        tasks = db.list_tasks(user_id=args.user)
        if not tasks:
            print(f"No tasks found for user '{args.user}'.")
            return
        print(f"=== PERSISTENT TASKS FOR USER '{args.user}' ===")
        for t in tasks:
            last_run = t["last_run_at"] or "Never"
            status = t["last_status"] or "Pending"
            count = get_result_count(t.get("last_result"))
            count_str = f" | Results: {count} item(s)" if count is not None else ""
            print(f"[{t['id']}] {t['name']} | Status: {status}{count_str} | Last Run: {last_run}")
            print(f"    Description: {t['task_description']}\n")

    elif args.command == "run-tasks":
        run_user_tasks(user_id=args.user)

    elif args.command == "run-task-by-id":
        try:
            updated_task = run_task_by_id(task_id=args.id)
            if updated_task and updated_task["last_result"]:
                print("=== EXTRACTION RESULT ===")
                print(updated_task["last_result"])
        except Exception as e:
            print(f"Execution Failed: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "show-results":
        tasks = db.list_tasks(user_id=args.user)
        if not tasks:
            print(f"No tasks found for user '{args.user}'.")
            return
        print(f"=== LATEST RUN RESULTS FOR USER '{args.user}' ===\n")
        for t in tasks:
            count = get_result_count(t.get("last_result"))
            count_str = f" ({count} items)" if count is not None else ""
            print(f"--- Task [{t['id']}] {t['name']} ---")
            print(f"Last Run : {t['last_run_at'] or 'Never'}")
            print(f"Status   : {t['last_status'] or 'Pending'}{count_str}")
            if t["last_error"]:
                print(f"Error    : {t['last_error']}")
            if t["last_result"]:
                print("Result   :")
                print(t["last_result"])
            elif not t["last_error"]:
                print("Result   : [No run result recorded yet]")
            print()

    elif args.command == "delete-task":
        success = db.delete_task(task_id=args.id, user_id=args.user)
        if success:
            print(f"✓ Task {args.id} deleted for user '{args.user}'.")
        else:
            print(f"✗ Task {args.id} not found for user '{args.user}'.", file=sys.stderr)

    elif args.description:
        try:
            result = run_task(task_description=args.description)
            print("=== EXTRACTION RESULT ===")
            print(result)
        except Exception as e:
            print(f"Task Failed: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
