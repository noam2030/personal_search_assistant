import { Task } from './types';
import { fetchUserTasks, createTask, updateTaskById, runTaskById, deleteTaskById, runAllTasks, API_BASE_URL } from './api';

// DOM Element References
const apiBaseUrlLink = document.getElementById('apiBaseUrlLink') as HTMLAnchorElement | null;
const apiBaseUrlText = document.getElementById('apiBaseUrlText') as HTMLSpanElement | null;
const userIdInput = document.getElementById('userIdInput') as HTMLInputElement;
const refreshTasksBtn = document.getElementById('refreshTasksBtn') as HTMLButtonElement;
const runAllTasksBtn = document.getElementById('runAllTasksBtn') as HTMLButtonElement;
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

    card.innerHTML = `
      <div class="task-header">
        <span class="task-name">${escapeHtml(task.name)}</span>
        <div class="task-status-actions">
          <span class="badge ${badgeClass}">${status}</span>
          <div class="task-actions">
            <button class="run-btn" data-id="${task.id}" ${isRunning ? 'disabled' : ''}>
              ${isRunning ? '<div class="spinner"></div> Running...' : 'Run Task'}
            </button>
            <button class="btn-secondary edit-btn" data-id="${task.id}" ${isRunning ? 'disabled' : ''}>✏️ Edit</button>
            <button class="btn-danger delete-btn" data-id="${task.id}" ${isRunning ? 'disabled' : ''}>Delete</button>
          </div>
        </div>
      </div>

      ${task.last_error ? `<div class="result-container" style="border: 1px solid var(--danger); margin-top: 1rem;"><pre style="color: var(--danger);">${escapeHtml(task.last_error)}</pre></div>` : ''}
      ${task.last_result ? renderResultSection(task.last_result, task.id) : ''}
    `;

    const runBtn = card.querySelector('.run-btn') as HTMLButtonElement;
    runBtn.addEventListener('click', () => handleRunTask(task.id));

    const editBtn = card.querySelector('.edit-btn') as HTMLButtonElement;
    editBtn.addEventListener('click', () => openModal('edit', task));

    const deleteBtn = card.querySelector('.delete-btn') as HTMLButtonElement;
    deleteBtn.addEventListener('click', () => handleDeleteTask(task.id));

    const expandBtn = card.querySelector('.expand-results-btn') as HTMLButtonElement | null;
    if (expandBtn) {
      expandBtn.addEventListener('click', () => {
        const extraContainer = card.querySelector(`#extra-results-${task.id}`) as HTMLDivElement | null;
        if (extraContainer) {
          const isHidden = extraContainer.classList.contains('hidden');
          const extraCount = expandBtn.getAttribute('data-extra-count') || '';
          if (isHidden) {
            extraContainer.classList.remove('hidden');
            expandBtn.innerHTML = '▲ Show less';
          } else {
            extraContainer.classList.add('hidden');
            expandBtn.innerHTML = `••• Show ${extraCount} more ${extraCount === '1' ? 'result' : 'results'}`;
          }
        }
      });
    }

    taskListContainer.appendChild(card);
  });
}

function renderResultSection(rawResult: string, taskId: number): string {
  return `
    <div class="result-container">
      ${renderVisualText(rawResult, taskId)}
    </div>
  `;
}

function renderVisualText(rawResult: string, taskId: number): string {
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

    const initialItems = items.slice(0, 4);
    const extraItems = items.slice(4);
    const cols = Math.min(initialItems.length, 4);

    const initialItemsHtml = initialItems.map((item) => renderSingleItemText(item)).join('');
    const extraItemsHtml = extraItems.map((item) => renderSingleItemText(item)).join('');
    const extraCount = extraItems.length;

    return `
      <div class="result-text-list">
        <div class="result-cards-grid" data-count="${cols}" style="--grid-columns: ${cols};">
          ${initialItemsHtml}
        </div>
        ${extraCount > 0 ? `
          <div class="extra-results-container hidden" id="extra-results-${taskId}">
            <div class="result-cards-grid" data-count="4" style="--grid-columns: 4;">
              ${extraItemsHtml}
            </div>
          </div>
          <button class="expand-results-btn" data-task-id="${taskId}" data-extra-count="${extraCount}">
            ••• Show ${extraCount} more ${extraCount === 1 ? 'result' : 'results'}
          </button>
        ` : ''}
      </div>
    `;
  } catch {
    return `<div class="result-text-content">${escapeHtml(rawResult)}</div>`;
  }
}

function extractWebsiteInfo(item: any, link: string | null): { name: string; url?: string } | null {
  // 1. Check explicit website / source / domain properties
  const siteKey = Object.keys(item).find((k) => /^(website|source|source_website|site|domain|publisher)$/i.test(k))
    || Object.keys(item).find((k) => /(website|source_website)/i.test(k));

  if (siteKey && item[siteKey]) {
    const rawVal = String(item[siteKey]).trim();
    if (rawVal) {
      if (/^https?:\/\//i.test(rawVal)) {
        try {
          const parsed = new URL(rawVal);
          return {
            name: parsed.hostname.replace(/^www\./i, ''),
            url: parsed.href,
          };
        } catch {
          return { name: rawVal, url: rawVal };
        }
      }
      return {
        name: rawVal,
        url: link || undefined,
      };
    }
  }

  // 2. Extract domain from link
  if (link) {
    try {
      const parsed = new URL(link);
      const host = parsed.hostname.replace(/^www\./i, '');
      if (host) {
        return {
          name: host,
          url: `${parsed.protocol}//${parsed.host}`,
        };
      }
    } catch {
      const match = link.match(/^(?:https?:\/\/)?(?:www\.)?([^\/\s]+)/i);
      if (match && match[1]) {
        return {
          name: match[1],
          url: link.startsWith('http') ? link : `https://${link}`,
        };
      }
    }
  }

  return null;
}

function renderSingleItemText(item: any): string {
  if (typeof item !== 'object' || item === null) {
    return `<div class="result-item-card"><div class="result-item-title">${escapeHtml(String(item))}</div></div>`;
  }

  const isNew = item.is_new === true;

  const titleKey = Object.keys(item).find((k) => /title|name|heading|event/i.test(k)) || Object.keys(item)[0];
  const title = titleKey ? String(item[titleKey]) : 'Extracted Item';

  const linkKey = Object.keys(item).find((k) => /^(link|url|href)$/i.test(k))
    || Object.keys(item).find((k) => /link|url|href/i.test(k));
  const link = linkKey ? String(item[linkKey]) : null;

  const descKey = Object.keys(item).find((k) => /desc|details|summary|text|info/i.test(k));
  const description = descKey && descKey !== titleKey ? String(item[descKey]) : null;

  const locationKey = Object.keys(item).find((k) => /^(location|venue|place|city|address)$/i.test(k))
    || Object.keys(item).find((k) => /location|venue|city/i.test(k));

  const siteKey = Object.keys(item).find((k) => /^(website|source|source_website|site|domain|publisher)$/i.test(k))
    || Object.keys(item).find((k) => /(website|source_website)/i.test(k));
  const websiteInfo = extractWebsiteInfo(item, link);

  const ignoredKeys = new Set([titleKey, linkKey, descKey, locationKey, siteKey, 'is_new'].filter(Boolean));

  const metaPills: string[] = [];

  if (isNew) {
    metaPills.push('<span class="result-pill result-pill-new">✨ NEW</span>');
  }

  if (websiteInfo) {
    const websiteHtml = websiteInfo.url
      ? `<a href="${escapeHtml(websiteInfo.url)}" target="_blank" rel="noopener" class="result-website-link">${escapeHtml(websiteInfo.name)}</a>`
      : escapeHtml(websiteInfo.name);
    metaPills.push(`<span class="result-pill result-pill-website"><strong>Website:</strong> ${websiteHtml}</span>`);
  }

  Object.entries(item).forEach(([k, v]) => {
    if (!ignoredKeys.has(k) && v !== null && v !== undefined && String(v).trim()) {
      metaPills.push(`<span class="result-pill"><strong>${escapeHtml(formatKey(k))}:</strong> ${escapeHtml(String(v))}</span>`);
    }
  });

  return `
    <div class="result-item-card ${isNew ? 'is-new-item' : ''}">
      <div class="result-item-title">
        ${isNew ? '<span class="item-badge-new">NEW</span> ' : ''}${escapeHtml(title)}
      </div>
      ${metaPills.length > 0 ? `<div class="result-pills-row">${metaPills.join('')}</div>` : ''}
      ${description ? `<div class="result-item-desc" title="${escapeHtml(description)}">${escapeHtml(description)}</div>` : ''}
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

let isRunningAll = false;

async function handleRunAllTasks(): Promise<void> {
  if (isRunningAll) return;
  const userId = userIdInput.value.trim() || 'noam';

  isRunningAll = true;
  runAllTasksBtn.disabled = true;
  runAllTasksBtn.innerHTML = '<div class="spinner"></div> Running All...';

  try {
    await runAllTasks(userId);
  } catch (error) {
    alert(`Batch execution failed: ${(error as Error).message}`);
  } finally {
    isRunningAll = false;
    runAllTasksBtn.disabled = false;
    runAllTasksBtn.innerHTML = 'Run All';
    await loadTasks();
  }
}

runAllTasksBtn.addEventListener('click', handleRunAllTasks);

// Helper functions
function escapeHtml(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function initApiBaseUrlDisplay(): void {
  if (apiBaseUrlLink && apiBaseUrlText) {
    apiBaseUrlLink.href = API_BASE_URL;
    apiBaseUrlText.textContent = API_BASE_URL;
    apiBaseUrlLink.title = `Connected to API Base URL: ${API_BASE_URL}`;
  }
}

// Initial Load
initApiBaseUrlDisplay();
loadTasks();
