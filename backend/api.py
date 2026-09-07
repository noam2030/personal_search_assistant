from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List

from backend import db
from backend.controller import run_task_by_id, run_user_tasks

router = APIRouter(prefix="/api")


class CreateTaskRequest(BaseModel):
    user_id: str
    task_description: str


class UpdateTaskRequest(BaseModel):
    task_description: Optional[str] = None
    name: Optional[str] = None


class TaskResponse(BaseModel):
    id: int
    user_id: str
    name: str
    task_description: str
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
    """Creates a new persistent natural language task from a single task_description string."""
    desc = req.task_description.strip() if req.task_description else ""
    if not req.user_id.strip() or not desc:
        raise HTTPException(status_code=400, detail="User ID and Task Description are required.")

    initial_name = desc[:40] + ("..." if len(desc) > 40 else "")
    task = db.add_task(user_id=req.user_id, name=initial_name, task_description=desc)
    return task


@router.put("/tasks/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, req: UpdateTaskRequest):
    """Updates an existing task's description or name."""
    existing = db.get_task(task_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found.")

    new_name = req.name.strip() if req.name and req.name.strip() else existing["name"]
    new_desc = req.task_description.strip() if req.task_description and req.task_description.strip() else existing["task_description"]

    updated_task = db.update_task_details(
        task_id=task_id, name=new_name, task_description=new_desc
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


router.post("/tasks/run-all", response_model=List[TaskResponse])(run_user_tasks)


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int, user_id: Optional[str] = Query(None)):
    """Deletes a task by ID."""
    success = db.delete_task(task_id=task_id, user_id=user_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found.")
    return {"status": "deleted", "id": task_id}
