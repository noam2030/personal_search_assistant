import { Task } from './types';
import { fetchUserTasks, createTask, updateTaskById, runTaskById, deleteTaskById } from './api';

// DOM Element References
const userIdInput = document.getElementById('userIdInput') as HTMLInputElement;
const refreshTasksBtn = document.getElementById('refreshTasksBtn') as HTMLButtonElement;
const openCreateTaskModalBtn = document.getElementById('openCreateTaskModalBtn') as HTMLButtonElement;
const closeTaskModalBtn = document.getElementById('closeTaskModalBtn') as HTMLButtonElement;
const cancelTaskModalBtn = document.getElementById('cancelTaskModalBtn') as HTMLButtonElement;
const taskModal = document.getElementById('taskModal') as HTMLDivElement;

const createTaskForm = document.getElementById('createTaskForm') as HTMLFormElement;
const taskNameInput = document.getElementById('taskName') as HTMLInputElement;
const taskUrlInput = document.getElementById('taskUrl') as HTMLInputElement;
const taskGoalInput = document.getElementById('taskGoal') as HTMLTextAreaElement;
const taskListContainer = document.getElementById('taskList') as HTMLDivElement;

// Running, Edit & View Mode State
const runningTasks: Record<number, boolean> = {};
const editingTasks: Record<number, boolean> = {};
const resultViewModes: Record<number, 'visual' | 'raw'> = {};

function openModal(): void {
  taskModal.classList.remove('hidden');
  taskNameInput.focus();
}

function closeModal(): void {
  taskModal.classList.add('hidden');
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
    const isEditing = !!editingTasks[task.id];
    const status = isRunning ? 'RUNNING' : (task.last_status || 'Pending');
    const badgeClass = isRunning
      ? 'badge-pending'
      : status === 'SUCCESS'
      ? 'badge-success'
      : status === 'FAILED'
      ? 'badge-failed'
      : 'badge-pending';

    const viewMode = resultViewModes[task.id] || 'visual';

    if (isEditing) {
      card.innerHTML = `
        <div class="task-header">
          <span class="task-name" style="color: #60a5fa;">✏️ Editing Task #${task.id}</span>
        </div>
        <div class="form-group" style="margin-top: 0.8rem;">
          <label>Task Name</label>
          <input type="text" class="edit-name-input" value="${escapeHtml(task.name)}" required>
        </div>
        <div class="form-group">
          <label>Target URL</label>
          <input type="url" class="edit-url-input" value="${escapeHtml(task.url)}" required>
        </div>
        <div class="form-group">
          <label>Extraction Goal</label>
          <textarea class="edit-goal-input" rows="2" required>${escapeHtml(task.goal)}</textarea>
        </div>
        <div class="task-actions">
          <button class="save-edit-btn" data-id="${task.id}">💾 Save Changes</button>
          <button class="btn-secondary cancel-edit-btn" data-id="${task.id}">Cancel</button>
        </div>
      `;

      const saveBtn = card.querySelector('.save-edit-btn') as HTMLButtonElement;
      saveBtn.addEventListener('click', () => handleSaveEdit(task.id, card));

      const cancelBtn = card.querySelector('.cancel-edit-btn') as HTMLButtonElement;
      cancelBtn.addEventListener('click', () => {
        delete editingTasks[task.id];
        loadTasks();
      });
    } else {
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
          <button class="btn-secondary edit-btn" data-id="${task.id}" ${isRunning ? 'disabled' : ''}>✏️ Edit</button>
          <button class="btn-danger delete-btn" data-id="${task.id}" ${isRunning ? 'disabled' : ''}>Delete</button>
        </div>

        ${task.last_error ? `<div class="result-container" style="border: 1px solid var(--danger); margin-top: 1rem;"><pre style="color: var(--danger);">${escapeHtml(task.last_error)}</pre></div>` : ''}
        ${task.last_result ? renderResultSection(task.last_result, viewMode) : ''}
      `;

      const runBtn = card.querySelector('.run-btn') as HTMLButtonElement;
      runBtn.addEventListener('click', () => handleRunTask(task.id));

      const editBtn = card.querySelector('.edit-btn') as HTMLButtonElement;
      editBtn.addEventListener('click', () => {
        editingTasks[task.id] = true;
        loadTasks();
      });

      const deleteBtn = card.querySelector('.delete-btn') as HTMLButtonElement;
      deleteBtn.addEventListener('click', () => handleDeleteTask(task.id));

      const visualToggle = card.querySelector('.toggle-visual') as HTMLButtonElement | null;
      const rawToggle = card.querySelector('.toggle-raw') as HTMLButtonElement | null;

      if (visualToggle && rawToggle) {
        visualToggle.addEventListener('click', () => {
          resultViewModes[task.id] = 'visual';
          loadTasks();
        });
        rawToggle.addEventListener('click', () => {
          resultViewModes[task.id] = 'raw';
          loadTasks();
        });
      }
    }

    taskListContainer.appendChild(card);
  });
}

async function handleSaveEdit(taskId: number, card: HTMLElement): Promise<void> {
  const nameInput = card.querySelector('.edit-name-input') as HTMLInputElement;
  const urlInput = card.querySelector('.edit-url-input') as HTMLInputElement;
  const goalInput = card.querySelector('.edit-goal-input') as HTMLTextAreaElement;

  const name = nameInput.value.trim();
  const url = urlInput.value.trim();
  const goal = goalInput.value.trim();

  if (!name || !url || !goal) {
    alert('Please fill out all fields (Name, URL, and Goal).');
    return;
  }

  try {
    await updateTaskById(taskId, { name, url, goal });
    delete editingTasks[taskId];
    await loadTasks();
  } catch (error) {
    alert(`Failed to update task: ${(error as Error).message}`);
  }
}

function renderResultSection(rawResult: string, viewMode: 'visual' | 'raw'): string {
  const visualActiveClass = viewMode === 'visual' ? 'active' : '';
  const rawActiveClass = viewMode === 'raw' ? 'active' : '';

  return `
    <div class="result-header">
      <span class="result-header-title">Extraction Results</span>
      <div class="view-toggle-group">
        <button class="toggle-btn toggle-visual ${visualActiveClass}">Visual Cards</button>
        <button class="toggle-btn toggle-raw ${rawActiveClass}">Raw JSON</button>
      </div>
    </div>
    <div class="result-container">
      ${viewMode === 'visual' ? renderVisualCards(rawResult) : `<pre>${escapeHtml(formatJson(rawResult))}</pre>`}
    </div>
  `;
}

function renderVisualCards(rawResult: string): string {
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

    const cardsHtml = items.map((item) => renderSingleItemCard(item)).join('');
    return `<div class="result-cards-grid">${cardsHtml}</div>`;
  } catch {
    return `<pre>${escapeHtml(rawResult)}</pre>`;
  }
}

function renderSingleItemCard(item: any): string {
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
openCreateTaskModalBtn.addEventListener('click', openModal);
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
  const name = taskNameInput.value.trim();
  const url = taskUrlInput.value.trim();
  const goal = taskGoalInput.value.trim();

  if (!name || !url || !goal) return;

  const submitBtn = createTaskForm.querySelector('button[type="submit"]') as HTMLButtonElement;
  submitBtn.disabled = true;

  try {
    await createTask({ user_id: userId, name, url, goal });
    closeModal();
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
