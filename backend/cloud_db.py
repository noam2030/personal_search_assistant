import os
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from google.cloud import firestore
    HAS_FIRESTORE = True
except ImportError:
    HAS_FIRESTORE = False

COLLECTION_NAME = "tasks"
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")


def get_firestore_client():
    """Returns a Firestore client instance if credentials/project are available."""
    if not HAS_FIRESTORE:
        return None
    try:
        return firestore.Client(project=GCP_PROJECT) if GCP_PROJECT else firestore.Client()
    except Exception as e:
        print(f"[Cloud DB Warning] Firestore client initialization skipped: {e}")
        return None


def _normalize_task_dict(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensures task_description field exists with backward compatibility for legacy 'goal'."""
    if task_data and "task_description" not in task_data:
        task_data["task_description"] = task_data.get("goal", "")
    return task_data


# -----------------------------------------------------------------------------
# Firestore Cloud Database Operations
# -----------------------------------------------------------------------------

def add_task_cloud(user_id: str, name: str, task_description: str) -> Dict[str, Any]:
    """Adds a task to Firestore cloud database."""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_firestore_client()

    if db:
        doc_ref = db.collection(COLLECTION_NAME).document()
        task_data = {
            "id": int(datetime.now().timestamp() * 1000) % 2147483647,
            "user_id": user_id,
            "name": name,
            "task_description": task_description,
            "goal": task_description,
            "url": "",
            "last_run_at": None,
            "last_status": None,
            "last_result": None,
            "last_error": None,
            "created_at": created_at,
        }
        doc_ref.set(task_data)
        return task_data

    raise RuntimeError("No cloud database client available.")


def list_tasks_cloud(user_id: str) -> List[Dict[str, Any]]:
    """Lists tasks for a user from Firestore."""
    db = get_firestore_client()
    if db:
        docs = (
            db.collection(COLLECTION_NAME)
            .where("user_id", "==", user_id)
            .stream()
        )
        tasks = [_normalize_task_dict(doc.to_dict()) for doc in docs]
        return sorted(tasks, key=lambda x: x.get("id", 0))

    return []


def get_task_cloud(task_id: int) -> Optional[Dict[str, Any]]:
    """Fetches a task by ID from Firestore."""
    db = get_firestore_client()
    if db:
        docs = (
            db.collection(COLLECTION_NAME)
            .where("id", "==", task_id)
            .limit(1)
            .stream()
        )
        for doc in docs:
            return _normalize_task_dict(doc.to_dict())

    return None


def update_task_details_cloud(
    task_id: int,
    name: str,
    task_description: str,
) -> Optional[Dict[str, Any]]:
    """Updates task name and task_description in Firestore."""
    db = get_firestore_client()
    if db:
        docs = db.collection(COLLECTION_NAME).where("id", "==", task_id).stream()
        for doc in docs:
            doc.reference.update(
                {
                    "name": name,
                    "task_description": task_description,
                    "goal": task_description,
                }
            )
            updated = doc.to_dict()
            updated.update({"name": name, "task_description": task_description, "goal": task_description})
            return _normalize_task_dict(updated)

    return None


def update_task_result_cloud(
    task_id: int,
    status: str,
    result_json: str | None = None,
    error: str | None = None,
):
    """Updates task execution results in Firestore."""
    db = get_firestore_client()
    if db:
        docs = db.collection(COLLECTION_NAME).where("id", "==", task_id).stream()
        last_run_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for doc in docs:
            doc.reference.update(
                {
                    "last_run_at": last_run_at,
                    "last_status": status,
                    "last_result": result_json,
                    "last_error": error,
                }
            )


def delete_task_cloud(task_id: int, user_id: str = None) -> bool:
    """Deletes a task from Firestore."""
    db = get_firestore_client()
    if db:
        docs = db.collection(COLLECTION_NAME).where("id", "==", task_id).stream()
        deleted = False
        for doc in docs:
            task_data = doc.to_dict()
            if not user_id or task_data.get("user_id") == user_id:
                doc.reference.delete()
                deleted = True
        return deleted

    return False
