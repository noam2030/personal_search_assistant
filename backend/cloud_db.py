import os
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    from google.cloud import firestore
    HAS_FIRESTORE = True
except ImportError:
    HAS_FIRESTORE = False

try:
    from google.cloud import storage
    HAS_GCS = True
except ImportError:
    HAS_GCS = False

COLLECTION_NAME = "tasks"
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
GCP_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "plenary-line-507307-g7")


def get_firestore_client():
    """Returns a Firestore client instance if credentials/project are available."""
    if not HAS_FIRESTORE:
        return None
    try:
        return firestore.Client(project=GCP_PROJECT)
    except Exception as e:
        print(f"[Cloud DB Warning] Firestore client initialization skipped: {e}")
        return None


def get_gcs_bucket():
    """Returns a GCS bucket instance if GCS_BUCKET_NAME is configured."""
    if not HAS_GCS or not GCS_BUCKET_NAME:
        return None
    try:
        client = storage.Client(project=GCP_PROJECT)
        return client.bucket(GCS_BUCKET_NAME)
    except Exception as e:
        print(f"[Cloud DB Warning] GCS bucket initialization skipped: {e}")
        return None


# -----------------------------------------------------------------------------
# Firestore / GCS Storage Operations
# -----------------------------------------------------------------------------

def add_task_cloud(user_id: str, name: str, url: str, goal: str) -> Dict[str, Any]:
    """Adds a task to Firestore / GCS cloud storage."""
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_firestore_client()

    if db:
        # Generates auto-increment numeric ID based on timestamp/counter
        doc_ref = db.collection(COLLECTION_NAME).document()
        task_data = {
            "id": int(datetime.now().timestamp() * 1000) % 2147483647,
            "user_id": user_id,
            "name": name,
            "url": url,
            "goal": goal,
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
        tasks = [doc.to_dict() for doc in docs]
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
            return doc.to_dict()

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
