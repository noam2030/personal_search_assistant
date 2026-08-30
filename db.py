import sqlite3
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE = "assistant.db"


def get_connection():
    """Returns a SQLite connection with dict-like row factory."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes the database schema if tables do not exist."""
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
        return get_task(task_id, user_id)


def list_tasks(user_id: str) -> List[Dict[str, Any]]:
    """Lists all tasks for a specific user."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY id ASC", (user_id,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_task(task_id: int, user_id: str = None) -> Optional[Dict[str, Any]]:
    """Fetches a single task by ID."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute(
                "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
            )
        else:
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


def delete_task(task_id: int, user_id: str) -> bool:
    """Deletes a task by ID for a user."""
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
        )
        conn.commit()
        return cursor.rowcount > 0
