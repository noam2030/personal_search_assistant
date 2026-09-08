import { Task } from './types';
import { fetchUserTasks, createTask, updateTaskById, runTaskById, deleteTaskById } from './api';

// DOM Element References
const userIdInput = document.getElementById('userIdInput') as HTMLInputElement;
const refreshTasksBtn = document.getElementById('refreshTasksBtn') as HTMLButtonElement;
const openCreateTaskModalBtn = document.getElementById('openCreateTaskModalBtn') as HTMLButtonElement;
const closeTaskModalBtn = document.getElementById('closeTaskModalBtn') as HTMLButtonElement;
const cancelTaskModalBtn = document.getElementById('cancelTaskModalBtn') as HTMLButtonElement;
const taskModal = document.getElementById('taskModal') as HTMLDivElement;
const modalTitle = document.getElementById('modalTitle') as HTMLHeadingElement;
const submitTaskBtnText = document.getElementById('submitTaskBtnText') as HTMLSpanElement;

const createTaskForm = document.getElementById('createTaskForm') as HTMLFormElement;
const taskDescriptionInput = document.getElementById('taskDescription') as HTMLTextAreaElement;
const taskListContainer = document.getElementById('taskList') as HTMLDivElement;

// Running & Editing State
const runningTasks: Record<number, boolean> = {};
let editingTaskId: number | null = null;

function openModal(mode: 'create' | 'edit', task?: Task): void {
  if (mode === 'edit' && task) {
    editingTaskId = task.id;
    modalTitle.textContent = `Edit Task: ${task.name}`;
    submitTaskBtnText.textContent = '💾 Save Changes';
    taskDescriptionInput.value = task.task_description;
  } else {
    editingTaskId = null;
    modalTitle.textContent = 'Create New Task';
    submitTaskBtnText.textContent = 'Create Task';
    createTaskForm.reset();
  }

  taskModal.classList.remove('hidden');
  taskDescriptionInput.focus();
}

function closeModal(): void {
  taskModal.classList.add('hidden');
  editingTaskId = null;
  createTaskForm.reset();
}

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

function getItemCount(rawResult?: string | null): number | null {
  if (!rawResult) return null;
  try {
    const cleanRaw = rawResult.replace(/^```json\s*/i, '').replace(/```\s*$/, '').trim();
    const parsed = JSON.parse(cleanRaw);
    if (Array.isArray(parsed)) return parsed.length;
    if (parsed && typeof parsed === 'object') {
      if (Array.isArray(parsed.items)) return parsed.items.length;
      if (Array.isArray(parsed.results)) return parsed.results.length;
      if (Array.isArray(parsed.events)) return parsed.events.length;
      if (Array.isArray(parsed.data)) return parsed.data.length;
    }
    return 0;
  } catch {
    return null;
  }
}

function renderTaskList(tasks: Task[]): void {
  if (tasks.length === 0) {
    taskListContainer.innerHTML = '<p style="color: var(--text-muted);">No persistent tasks found. Click "➕ New Task" above to create your first task!</p>';
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

    const resultCount = getItemCount(task.last_result);
    const countBadge = resultCount !== null
      ? `<span class="badge" style="background: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.3); font-weight: 600;">📊 ${resultCount} ${resultCount === 1 ? 'Result' : 'Results'}</span>`
      : '';

    card.innerHTML = `
      <div class="task-header">
        <span class="task-name">${escapeHtml(task.name)}</span>
        <div style="display: flex; gap: 0.5rem; align-items: center;">
          ${countBadge}
          <span class="badge ${badgeClass}">${status}</span>
        </div>
      </div>
      <div class="task-detail"><strong>Task Description:</strong> ${escapeHtml(task.task_description)}</div>
      <div class="task-detail" style="font-size: 0.75rem;"><strong>Last Run:</strong> ${task.last_run_at || 'Never'}</div>
      
      <div class="task-actions">
        <button class="run-btn" data-id="${task.id}" ${isRunning ? 'disabled' : ''}>
          ${isRunning ? '<div class="spinner"></div> Running...' : '▶ Run Task'}
        </button>
        <button class="btn-secondary edit-btn" data-id="${task.id}" ${isRunning ? 'disabled' : ''}>✏️ Edit</button>
        <button class="btn-danger delete-btn" data-id="${task.id}" ${isRunning ? 'disabled' : ''}>Delete</button>
      </div>

      ${task.last_error ? `<div class="result-container" style="border: 1px solid var(--danger); margin-top: 1rem;"><pre style="color: var(--danger);">${escapeHtml(task.last_error)}</pre></div>` : ''}
      ${task.last_result ? renderResultSection(task.last_result) : ''}
    `;

    const runBtn = card.querySelector('.run-btn') as HTMLButtonElement;
    runBtn.addEventListener('click', () => handleRunTask(task.id));

    const editBtn = card.querySelector('.edit-btn') as HTMLButtonElement;
    editBtn.addEventListener('click', () => openModal('edit', task));

    const deleteBtn = card.querySelector('.delete-btn') as HTMLButtonElement;
    deleteBtn.addEventListener('click', () => handleDeleteTask(task.id));

    taskListContainer.appendChild(card);
  });
}

function renderResultSection(rawResult: string): string {
  const count = getItemCount(rawResult);
  const countLabel = count !== null ? ` (${count} ${count === 1 ? 'item' : 'items'})` : '';

  return `
    <div class="result-header">
      <span class="result-header-title">Extraction Results${countLabel}</span>
    </div>
    <div class="result-container">
      ${renderVisualText(rawResult)}
    </div>
  `;
}

function renderVisualText(rawResult: string): string {
  try {
    const cleanRaw = rawResult.replace(/^```json\s*/i, '').replace(/```\s*$/, '').trim();
    const parsed = JSON.parse(cleanRaw);

    let items: any[] = [];
    let reason: string | null = null;

    if (Array.isArray(parsed)) {
      items = parsed;
    } else if (parsed && typeof parsed === 'object') {
      if (Array.isArray(parsed.items)) items = parsed.items;
      else if (Array.isArray(parsed.results)) items = parsed.results;
      else if (Array.isArray(parsed.events)) items = parsed.events;
      else if (Array.isArray(parsed.data)) items = parsed.data;

      if (parsed.reason) reason = parsed.reason;
    }

    if (items.length === 0) {
      return `
        <div class="empty-result-card">
          <p>🔍 No matching items found.</p>
          ${reason ? `<p style="font-size: 0.8rem; margin-top: 0.4rem; color: var(--text-muted);">${escapeHtml(reason)}</p>` : ''}
        </div>
      `;
    }

    const itemsHtml = items.map((item) => renderSingleItemText(item)).join('');
    return `<div class="result-text-list">${itemsHtml}</div>`;
  } catch {
    return `<div class="result-text-content">${escapeHtml(rawResult)}</div>`;
  }
}

function renderSingleItemText(item: any): string {
  if (typeof item !== 'object' || item === null) {
    return `<div class="result-item-card"><div class="result-item-title">${escapeHtml(String(item))}</div></div>`;
  }

  const titleKey = Object.keys(item).find((k) => /title|name|heading|event/i.test(k)) || Object.keys(item)[0];
  const title = titleKey ? String(item[titleKey]) : 'Extracted Item';

  const linkKey = Object.keys(item).find((k) => /link|url|href|website/i.test(k));
  const link = linkKey ? String(item[linkKey]) : null;

  const descKey = Object.keys(item).find((k) => /desc|details|summary|text|info/i.test(k));
  const description = descKey && descKey !== titleKey ? String(item[descKey]) : null;

  const ignoredKeys = new Set([titleKey, linkKey, descKey].filter(Boolean));
  const pills = Object.entries(item)
    .filter(([k]) => !ignoredKeys.has(k))
    .map(([k, v]) => `<span class="result-pill"><strong>${escapeHtml(formatKey(k))}:</strong> ${escapeHtml(String(v))}</span>`)
    .join('');

  return `
    <div class="result-item-card">
      <div class="result-item-title">${escapeHtml(title)}</div>
      ${pills ? `<div class="result-pills-row">${pills}</div>` : ''}
      ${description ? `<div class="result-item-desc">${escapeHtml(description)}</div>` : ''}
      ${link ? `<a href="${escapeHtml(link)}" target="_blank" rel="noopener" class="result-link-btn">View Details ↗</a>` : ''}
    </div>
  `;
}

function formatKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
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

// Modal Event Listeners
openCreateTaskModalBtn.addEventListener('click', () => openModal('create'));
closeTaskModalBtn.addEventListener('click', closeModal);
cancelTaskModalBtn.addEventListener('click', closeModal);

taskModal.addEventListener('click', (e) => {
  if (e.target === taskModal) closeModal();
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !taskModal.classList.contains('hidden')) {
    closeModal();
  }
});

createTaskForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const userId = userIdInput.value.trim() || 'noam';
  const task_description = taskDescriptionInput.value.trim();

  if (!task_description) return;

  const submitBtn = createTaskForm.querySelector('button[type="submit"]') as HTMLButtonElement;
  submitBtn.disabled = true;

  try {
    if (editingTaskId !== null) {
      // Editing existing task
      await updateTaskById(editingTaskId, { task_description });
    } else {
      // Creating new task
      await createTask({ user_id: userId, task_description });
    }
    closeModal();
    await loadTasks();
  } catch (error) {
    alert(`Failed to save task: ${(error as Error).message}`);
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

// Initial Load
loadTasks();
