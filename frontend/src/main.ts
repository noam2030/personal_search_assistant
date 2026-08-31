import { Task } from './types';
import { fetchUserTasks, createTask, runTaskById, deleteTaskById } from './api';

// DOM Element References
const userIdInput = document.getElementById('userIdInput') as HTMLInputElement;
const refreshTasksBtn = document.getElementById('refreshTasksBtn') as HTMLButtonElement;
const createTaskForm = document.getElementById('createTaskForm') as HTMLFormElement;
const taskNameInput = document.getElementById('taskName') as HTMLInputElement;
const taskUrlInput = document.getElementById('taskUrl') as HTMLInputElement;
const taskGoalInput = document.getElementById('taskGoal') as HTMLTextAreaElement;
const taskListContainer = document.getElementById('taskList') as HTMLDivElement;

// Running State Map (taskId -> boolean)
const runningTasks: Record<number, boolean> = {};

async function loadTasks(): Promise<void> {
  const userId = userIdInput.value.trim() || 'noam';
  taskListContainer.innerHTML = '<p style="color: var(--text-muted);">Loading tasks...</p>';

  try {
    const tasks = await fetchUserTasks(userId);
    renderTaskList(tasks);
  } catch (error) {
    taskListContainer.innerHTML = `<p style="color: var(--danger);">Error loading tasks: ${(error as Error).message}</p>`;
  }
}

function renderTaskList(tasks: Task[]): void {
  if (tasks.length === 0) {
    taskListContainer.innerHTML = '<p style="color: var(--text-muted);">No persistent tasks found. Create your first task on the left!</p>';
    return;
  }

  taskListContainer.innerHTML = '';
  tasks.forEach((task) => {
    const card = document.createElement('div');
    card.className = 'task-card';

    const isRunning = !!runningTasks[task.id];
    const status = isRunning ? 'RUNNING' : (task.last_status || 'Pending');
    const badgeClass = isRunning
      ? 'badge-pending'
      : status === 'SUCCESS'
      ? 'badge-success'
      : status === 'FAILED'
      ? 'badge-failed'
      : 'badge-pending';

    card.innerHTML = `
      <div class="task-header">
        <span class="task-name">${escapeHtml(task.name)}</span>
        <span class="badge ${badgeClass}">${status}</span>
      </div>
      <div class="task-detail"><strong>URL:</strong> <a href="${escapeHtml(task.url)}" target="_blank" rel="noopener">${escapeHtml(task.url)}</a></div>
      <div class="task-detail"><strong>Goal:</strong> ${escapeHtml(task.goal)}</div>
      <div class="task-detail" style="font-size: 0.75rem;"><strong>Last Run:</strong> ${task.last_run_at || 'Never'}</div>
      
      <div class="task-actions">
        <button class="run-btn" data-id="${task.id}" ${isRunning ? 'disabled' : ''}>
          ${isRunning ? '<div class="spinner"></div> Running...' : '▶ Run Task'}
        </button>
        <button class="btn-danger delete-btn" data-id="${task.id}" ${isRunning ? 'disabled' : ''}>Delete</button>
      </div>

      ${task.last_error ? `<div class="result-container" style="border: 1px solid var(--danger);"><pre style="color: var(--danger);">${escapeHtml(task.last_error)}</pre></div>` : ''}
      ${task.last_result ? `<div class="result-container"><pre>${escapeHtml(formatJson(task.last_result))}</pre></div>` : ''}
    `;

    // Event Listeners
    const runBtn = card.querySelector('.run-btn') as HTMLButtonElement;
    runBtn.addEventListener('click', () => handleRunTask(task.id));

    const deleteBtn = card.querySelector('.delete-btn') as HTMLButtonElement;
    deleteBtn.addEventListener('click', () => handleDeleteTask(task.id));

    taskListContainer.appendChild(card);
  });
}

async function handleRunTask(taskId: number): Promise<void> {
  runningTasks[taskId] = true;
  await loadTasks();

  try {
    await runTaskById(taskId);
  } catch (error) {
    alert(`Task Execution Failed: ${(error as Error).message}`);
  } finally {
    delete runningTasks[taskId];
    await loadTasks();
  }
}

async function handleDeleteTask(taskId: number): Promise<void> {
  const userId = userIdInput.value.trim() || 'noam';
  if (!confirm('Are you sure you want to delete this task?')) return;

  try {
    await deleteTaskById(taskId, userId);
    await loadTasks();
  } catch (error) {
    alert(`Failed to delete task: ${(error as Error).message}`);
  }
}

createTaskForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const userId = userIdInput.value.trim() || 'noam';
  const name = taskNameInput.value.trim();
  const url = taskUrlInput.value.trim();
  const goal = taskGoalInput.value.trim();

  if (!name || !url || !goal) return;

  const submitBtn = createTaskForm.querySelector('button[type="submit"]') as HTMLButtonElement;
  submitBtn.disabled = true;

  try {
    await createTask({ user_id: userId, name, url, goal });
    createTaskForm.reset();
    await loadTasks();
  } catch (error) {
    alert(`Failed to create task: ${(error as Error).message}`);
  } finally {
    submitBtn.disabled = false;
  }
});

refreshTasksBtn.addEventListener('click', () => loadTasks());
userIdInput.addEventListener('change', () => loadTasks());

// Helper functions
function escapeHtml(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatJson(raw: string): string {
  try {
    const cleanRaw = raw.replace(/^```json\s*/i, '').replace(/```\s*$/, '').trim();
    const parsed = JSON.parse(cleanRaw);
    return JSON.stringify(parsed, null, 2);
  } catch {
    return raw;
  }
}

// Initial Load
loadTasks();
