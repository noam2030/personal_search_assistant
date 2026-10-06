import { Task, CreateTaskPayload, UpdateTaskPayload } from './types';

/**
 * Resolves the backend API base URL.
 * Priority:
 * 1. Explicit VITE_API_URL environment variable if provided at build time.
 * 2. If running in a browser on Vercel preview/staging (*.vercel.app branch/preview),
 *    route to the Cloud Run Staging service.
 * 3. If running on Vercel production domain, route to Cloud Run Production service.
 * 4. Fallback to local FastAPI development server (http://localhost:8000).
 */
export function resolveApiBaseUrl(): string {
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL.replace(/\/$/, '');
  }
  if (typeof window !== 'undefined' && window.location?.hostname) {
    const hostname = window.location.hostname.toLowerCase();
    if (hostname.endsWith('vercel.app')) {
      // Vercel Preview / Git branch / staging environments
      if (
        hostname.includes('git-') ||
        hostname.includes('staging') ||
        hostname.includes('preview') ||
        hostname.includes('-preview-')
      ) {
        return 'https://personal-search-assistant-api-staging-6dekvxzgaq-uc.a.run.app';
      }
      // Vercel Production deployment
      return 'https://personal-search-assistant-api-6dekvxzgaq-uc.a.run.app';
    }
  }
  return 'http://localhost:8000';
}

export const API_BASE_URL = resolveApiBaseUrl();

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

export async function updateTaskById(taskId: number, payload: UpdateTaskPayload): Promise<Task> {
  const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || 'Failed to update task');
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

export async function runAllTasks(userId: string): Promise<Task[]> {
  const response = await fetch(`${API_BASE_URL}/api/tasks/run-all?user_id=${encodeURIComponent(userId)}`, {
    method: 'POST',
  });
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || 'Batch task execution failed');
  }
  return response.json();
}
