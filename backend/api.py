from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Dict, Any

from backend import db
from backend.controller import run_task_by_id

router = APIRouter(prefix="/api")


class CreateTaskRequest(BaseModel):
    user_id: str
    name: str
    url: str
    goal: str


class UpdateTaskRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    goal: Optional[str] = None


class TaskResponse(BaseModel):
    id: int
    user_id: str
    name: str
    url: str
    goal: str
    last_run_at: Optional[str] = None
    last_status: Optional[str] = None
    last_result: Optional[str] = None
    last_error: Optional[str] = None
    created_at: str


@router.get("/health")
def health_check():
    """Simple API health check endpoint."""
    return {"status": "ok", "service": "personal_search_assistant"}


@router.get("/tasks", response_model=List[TaskResponse])
def list_tasks(user_id: str = Query(..., description="User ID to list tasks for")):
    """Returns all tasks for a specific user."""
    tasks = db.list_tasks(user_id)
    return tasks


@router.post("/tasks", response_model=TaskResponse, status_code=201)
def create_task(req: CreateTaskRequest):
    """Creates a new persistent task."""
    if not req.user_id.strip() or not req.name.strip() or not req.url.strip() or not req.goal.strip():
        raise HTTPException(status_code=400, detail="All fields (user_id, name, url, goal) are required.")

    task = db.add_task(user_id=req.user_id, name=req.name, url=req.url, goal=req.goal)
    return task


@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, req: UpdateTaskRequest):
    """Updates an existing task's name, URL, or extraction goal."""
    existing = db.get_task(task_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found.")

    new_name = req.name.strip() if req.name and req.name.strip() else existing["name"]
    new_url = req.url.strip() if req.url and req.url.strip() else existing["url"]
    new_goal = req.goal.strip() if req.goal and req.goal.strip() else existing["goal"]

    updated_task = db.update_task_details(
        task_id=task_id, name=new_name, url=new_url, goal=new_goal
    )
    if not updated_task:
        raise HTTPException(status_code=500, detail="Failed to update task details.")

    return updated_task


@router.post("/tasks/{task_id}/run", response_model=TaskResponse)
def execute_task(task_id: int):
    """Triggers live execution of a task by ID and returns updated task with results."""
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found.")

    try:
        updated_task = run_task_by_id(task_id=task_id)
        return updated_task
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task execution failed: {str(e)}")


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, user_id: Optional[str] = Query(None)):
    """Deletes a task by ID."""
    success = db.delete_task(task_id=task_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found.")
    return {"status": "deleted", "id": task_id}
