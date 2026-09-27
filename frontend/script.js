// ============================================================================
// Waypoint — frontend logic
// Talks to the Flask backend over the REST API defined in backend/app.py
// ============================================================================

// While developing locally (file:// or 127.0.0.1/localhost), talk to the
// local Flask server. Once deployed, talk to the live backend instead.
const isLocal =
  location.protocol === "file:" ||
  location.hostname === "127.0.0.1" ||
  location.hostname === "localhost";

const API_BASE = isLocal
  ? "http://127.0.0.1:5000/api"
  : "https://waypoint-task-manager-1.onrender.com/api";

// ---- state ------------------------------------------------------------
let projects = [];
let currentProjectId = null;
let currentTasks = [];
let priorityFilter = "all";

// ---- element refs -------------------------------------------------------
const routeList = document.getElementById("routeList");
const newProjectBtn = document.getElementById("newProjectBtn");
const newProjectForm = document.getElementById("newProjectForm");
const cancelProjectBtn = document.getElementById("cancelProjectBtn");
const projectNameInput = document.getElementById("projectNameInput");
const projectDescInput = document.getElementById("projectDescInput");

const emptyState = document.getElementById("emptyState");
const boardContent = document.getElementById("boardContent");
const projectTitle = document.getElementById("projectTitle");
const projectDesc = document.getElementById("projectDesc");
const renameProjectBtn = document.getElementById("renameProjectBtn");
const deleteProjectBtn = document.getElementById("deleteProjectBtn");
const priorityFilterBar = document.getElementById("priorityFilter");

const connStatus = document.getElementById("connStatus");
const connStatusText = document.getElementById("connStatusText");

const taskModalOverlay = document.getElementById("taskModalOverlay");
const taskModalTitle = document.getElementById("taskModalTitle");
const taskForm = document.getElementById("taskForm");
const taskIdInput = document.getElementById("taskId");
const taskStatusInput = document.getElementById("taskStatus");
const taskTitleInput = document.getElementById("taskTitleInput");
const taskDescInput = document.getElementById("taskDescInput");
const taskPriorityInput = document.getElementById("taskPriorityInput");
const taskDueInput = document.getElementById("taskDueInput");
const closeTaskModalBtn = document.getElementById("closeTaskModalBtn");
const deleteTaskBtn = document.getElementById("deleteTaskBtn");

const STATUSES = ["todo", "in_progress", "done"];

// ---- API helper -----------------------------------------------------------

async function api(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res.json();
}

// ---- connection status ------------------------------------------------

async function checkConnection() {
  try {
    await api("/health");
    connStatus.classList.add("online");
    connStatus.classList.remove("offline");
    connStatusText.textContent = "Backend connected";
  } catch (e) {
    connStatus.classList.add("offline");
    connStatus.classList.remove("online");
    connStatusText.textContent = "Backend not reachable — is app.py running?";
  }
}

// ---- projects -----------------------------------------------------------

async function loadProjects() {
  try {
    projects = await api("/projects");
    renderProjectList();
    if (currentProjectId && !projects.find((p) => p.id === currentProjectId)) {
      currentProjectId = null;
    }
    if (currentProjectId) {
      renderBoardHeader();
    } else if (projects.length === 0) {
      showEmptyState();
    }
  } catch (e) {
    console.error(e);
  }
}

function renderProjectList() {
  routeList.innerHTML = "";
  projects.forEach((p) => {
    const item = document.createElement("div");
    item.className = "route-item" + (p.id === currentProjectId ? " active" : "");
    item.innerHTML = `
      <button class="route-item-delete" title="Delete route">&times;</button>
      <span class="route-item-name">${escapeHtml(p.name)}</span>
      <span class="route-item-meta">${p.task_counts.total} task${p.task_counts.total === 1 ? "" : "s"} &middot; ${p.task_counts.done} done</span>
    `;
    item.addEventListener("click", () => selectProject(p.id));
    item.querySelector(".route-item-delete").addEventListener("click", (ev) => {
      ev.stopPropagation();
      deleteProject(p.id);
    });
    routeList.appendChild(item);
  });
}

async function selectProject(id) {
  currentProjectId = id;
  renderProjectList();
  await renderBoardHeader();
  await loadTasks();
}

async function renderBoardHeader() {
  const project = projects.find((p) => p.id === currentProjectId);
  if (!project) {
    showEmptyState();
    return;
  }
  emptyState.classList.add("hidden");
  boardContent.classList.remove("hidden");
  projectTitle.textContent = project.name;
  projectDesc.textContent = project.description || "No description yet.";
}

function showEmptyState() {
  boardContent.classList.add("hidden");
  emptyState.classList.remove("hidden");
}

newProjectBtn.addEventLi