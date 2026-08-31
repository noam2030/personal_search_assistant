import argparse
import json
import sys
from backend.controller import run_task, run_user_tasks, run_task_by_id
from backend import db


def main():
    parser = argparse.ArgumentParser(
        description="Personal Search Assistant Agent - Task Manager & AI Extractor"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: add-task
    add_parser = subparsers.add_parser("add-task", help="Add a new persistent task for a user")
    add_parser.add_argument("--user", type=str, required=True, help="User ID (e.g. 'noam')")
    add_parser.add_argument("--name", type=str, required=True, help="Task name (e.g. 'Android Jobs')")
    add_parser.add_argument("--url", type=str, required=True, help="Target URL to crawl")
    add_parser.add_argument("--goal", type=str, required=True, help="Extraction goal / prompt")

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

    # Fallback options for single run mode: --url and --goal
    parser.add_argument("--url", type=str, help="Target URL (single-run mode)")
    parser.add_argument("--goal", type=str, help="Extraction goal (single-run mode)")

    args = parser.parse_args()

    # Handle subcommands
    if args.command == "add-task":
        task = db.add_task(user_id=args.user, name=args.name, url=args.url, goal=args.goal)
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
            print(f"[{t['id']}] {t['name']} | Status: {status} | Last Run: {last_run}")
            print(f"    URL : {t['url']}")
            print(f"    Goal: {t['goal']}\n")

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
            print(f"--- Task [{t['id']}] {t['name']} ---")
            print(f"Last Run : {t['last_run_at'] or 'Never'}")
            print(f"Status   : {t['last_status'] or 'Pending'}")
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

    elif args.url and args.goal:
        # Backward-compatible single-run execution mode
        try:
            result = run_task(url=args.url, goal=args.goal)
            print("=== EXTRACTION RESULT ===")
            print(result)
        except Exception as e:
            print(f"Task Failed: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
