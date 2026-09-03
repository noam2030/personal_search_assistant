import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend import cloud_db

DB_FILE = os.getenv("DATABASE_PATH", "assistant.db")


def is_cloud_available() -> bool:
    """
    Checks if Cloud DB (Firestore) is active.
    Automatically active when running in Google Cloud Run (K_SERVICE is set)
    or when ENABLE_CLOUD_DB=true is explicitly configured.
    """
    is_in_cloud_run = os.getenv("K_SERVICE") is not None
    is_explicitly_enabled = os.getenv("ENABLE_CLOUD_DB", "false").lower() in ("true", "1")
    return (is_in_cloud_run or is_explicitly_enabled) and cloud_db.get_firestore_client() is not None


def get_connection():
    """Returns a SQLite connection with dict-like row factory."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the database schema if tables do not exist."""
    if is_cloud_available():
        return
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                goal TEXT NOT NULL,
                last_run_at TEXT,
                last_status TEXT,
                last_result TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def add_task(user_id: str, name: str, url: str, goal: str) -> Dict[str, Any]:
    """Adds a new persistent task for a user."""
    if is_cloud_available():
        return cloud_db.add_task_cloud(user_id=user_id, name=name, url=url, goal=goal)

    init_db()
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO tasks (user_id, name, url, goal, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, name, url, goal, created_at),
        )
        conn.commit()
        task_id = cursor.lastrowid
        return get_task(task_id)


def list_tasks(user_id: str) -> List[Dict[str, Any]]:
    """Lists all tasks for a specific user."""
    if is_cloud_available():
        return cloud_db.list_tasks_cloud(user_id=user_id)

    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY id ASC", (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a single task by ID."""
    if is_cloud_available():
        return cloud_db.get_task_cloud(task_id=task_id)

    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_task_result(
    task_id: int,
    status: str,
    result_json: str | None = None,
    error: str | None = None,
):
    """Updates the task row with the latest execution status and result."""
    if is_cloud_available():
        cloud_db.update_task_result_cloud(
            task_id=task_id,
            status=status,
            result_json=result_json,
            error=error,
        )
        return

    init_db()
    last_run_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE tasks
            SET last_run_at = ?, last_status = ?, last_result = ?, last_error = ?
            WHERE id = ?
            """,
            (last_run_at, status, result_json, error, task_id),
        )
        conn.commit()


def delete_task(task_id: int, user_id: str = None) -> bool:
    """Deletes a task by ID."""
    if is_cloud_available():
        return cloud_db.delete_task_cloud(task_id=task_id, user_id=user_id)

    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute(
                "DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
            )
        else:
            cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        return cursor.rowcount > 0
