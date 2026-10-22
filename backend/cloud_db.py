import os
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from google.cloud import firestore
    HAS_FIRESTORE = True
except ImportError:
    HAS_FIRESTORE = False

ROOT_COLLECTION = "personal-search-assistant"
TASKS_SUBCOLLECTION = "tasks"
COLLECTION_NAME = ROOT_COLLECTION
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


def get_user_doc_ref(db, user_id: str):
    """Returns the Firestore document reference for a user under the root app collection."""
    return db.collection(ROOT_COLLECTION).document(user_id)


def get_user_tasks_collection(db, user_id: str):
    """Returns the tasks subcollection under personal-search-assistant/{user_id}/tasks."""
    return get_user_doc_ref(db, user_id).collection(TASKS_SUBCOLLECTION)


def _iter_matching_task_docs(db, task_id: int, user_id: Optional[str] = None):
    """Yields task DocumentSnapshots matching task_id under user_id or across all users."""
    if user_id:
        docs = (
            get_user_tasks_collection(db, user_id)
            .where("id", "==", task_id)
            .stream()
        )
        for doc in docs:
            yield doc
        return

    # Search across user documents in personal-search-assistant root collection
    for user_doc in db.collection(ROOT_COLLECTION).stream():
        docs = (
            user_doc.reference.collection(TASKS_SUBCOLLECTION)
            .where("id", "==", task_id)
            .stream()
        )
        for doc in docs:
            yield doc


# -----------------------------------------------------------------------------
# Firestore Cloud Database Operations
# -----------------------------------------------------------------------------

def add_task_cloud(user_id: str, name: str, task_description: str) -> Dict[str, Any]:
    """Adds a task to Firestore under personal-search-assistant/{user_id}/tasks."""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_firestore_client()

    if db:
        task_id = int(datetime.now().timestamp() * 1000) % 2147483647
        user_doc_ref = get_user_doc_ref(db, user_id)
        user_doc_ref.set({"user_id": user_id, "updated_at": created_at}, merge=True)

        doc_ref = get_user_tasks_collection(db, user_id).document(str(task_id))
        task_data = {
            "id": task_id,
            "user_id": user_id,
            "name": name,
            "task_description": task_description,
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
    """Lists tasks for a user from Firestore under personal-search-assistant/{user_id}/tasks."""
    db = get_firestore_client()
    if db:
        docs = get_user_tasks_collection(db, user_id).stream()
        tasks = [doc.to_dict() for doc in docs]
        return sorted(tasks, key=lambda x: x.get("id", 0))

    return []


def get_task_cloud(task_id: int, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetches a task by ID from Firestore."""
    db = get_firestore_client()
    if db:
        for doc in _iter_matching_task_docs(db, task_id=task_id, user_id=user_id):
            return doc.to_dict()

    return None


def update_task_details_cloud(
    task_id: int,
    name: str,
    task_description: str,
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Updates task name and task_description in Firestore."""
    db = get_firestore_client()
    if db:
        for doc in _iter_matching_task_docs(db, task_id=task_id, user_id=user_id):
            doc.reference.update(
                {
                    "name": name,
                    "task_description": task_description,
                }
            )
            updated = doc.to_dict()
            updated.update({"name": name, "task_description": task_description})
            return updated

    return None


def update_task_result_cloud(
    task_id: int,
    status: str,
    result_json: str | None = None,
    error: str | None = None,
    user_id: Optional[str] = None,
):
    """Updates task execution results in Firestore."""
    db = get_firestore_client()
    if db:
        last_run_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for doc in _iter_matching_task_docs(db, task_id=task_id, user_id=user_id):
            doc.reference.update(
                {
                    "last_run_at": last_run_at,
                    "last_status": status,
                    "last_result": result_json,
                    "last_error": error,
                }
            )


def delete_task_cloud(task_id: int, user_id: Optional[str] = None) -> bool:
    """Deletes a task from Firestore."""
    db = get_firestore_client()
    if db:
        deleted = False
        for doc in _iter_matching_task_docs(db, task_id=task_id, user_id=user_id):
            task_data = doc.to_dict()
            if not user_id or task_data.get("user_id") == user_id:
                doc.reference.delete()
                deleted = True
        return deleted

    return False
