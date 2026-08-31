import { Task, CreateTaskPayload } from './types';

// Reads API URL from environment variable in Vercel or defaults to local FastAPI
const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');

export async function fetchUserTasks(userId: string): Promise<Task[]> {
  const response = await fetch(`${API_BASE_URL}/api/tasks?user_id=${encodeURIComponent(userId)}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch tasks: ${response.statusText}`);
  }
  return response.json();
}

export async function createTask(payload: CreateTaskPayload): Promise<Task> {
  const response = await fetch(`${API_BASE_URL}/api/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || 'Failed to create task');
  }
  return response.json();
}

export async function runTaskById(taskId: number): Promise<Task> {
  const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/run`, {
    method: 'POST',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || 'Task execution failed');
  }
  return response.json();
}

export async function deleteTaskById(taskId: number, userId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}?user_id=${encodeURIComponent(userId)}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    throw new Error(`Failed to delete task: ${response.statusText}`);
  }
}
