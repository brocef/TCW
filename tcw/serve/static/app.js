// ============================================================
// MANUAL SMOKE CHECKLIST (Phase 3 - Frontend editor architecture)
// ============================================================
//
// Run these manually after each change:
// 1.  Edit save:       Click "Edit" on a work item -> change a field or body -> "Save"
//                        -> item updates in detail view, dirty indicator clears
// 2.  Cancel (dirty):  Click "Edit" -> make changes -> "Cancel"
//                        -> confirmation dialog appears -> confirming returns to view
// 3.  Cancel (clean):  Click "Edit" -> "Cancel" (no changes made)
//                        -> no confirmation, returns to view immediately
// 4.  Validation err:  Click "Edit" -> send save -> if server returns 422
//                        -> error renders inline in red banner above fields
// 5.  Stale 409:       Edit item A in browser -> modify A via CLI
//                        -> click "Save" -> conflict banner appears, draft preserved in editor
//                        -> "Refresh" replaces draft with server version
//                        -> "Discard" abandons edit, returns to view
// 6.  Dirty nav (item):Make changes in editor -> click a different list item
//                        -> warning dialog appears; confirming exits editor
// 7.  Dirty nav (tab): Make changes in editor -> switch axis tab
//                        -> warning dialog appears; confirming exits editor
// 8.  Dirty nav (close):Make changes in editor -> try to close browser tab
//                        -> browser beforeunload warning appears
// 9.  Markdown editor: In edit mode, type in the textarea -> right pane preview updates live
// 10. Artifact edit:   Click the pencil next to a present artifact -> Markdown editor opens
//                        -> edit content -> "Save" -> artifact updates, returns to detail view
// 11. Browse intact:   List/detail/filter tabs work as before -- no regressions
//
// TODO (Phase 4): Create work item form, taxonomy/capability editors, lifecycle actions

// ============================================================
// STATE
// ============================================================

const state = {
  view: "work",
  data: { work: [], taxonomy: [], capabilities: [] },
  selected: null,
  filter: "",
  cachedWorkDetail: null, // payload cached by renderWork for editor use
};

const labels = {
  work: "Work",
  taxonomy: "Taxonomy",
  capabilities: "Capabilities",
};

// ============================================================
// EDITOR STATE MACHINE
// ============================================================

const editor = {
  mode: null,        // null | 'core' | 'artifact' | 'sidecar'
  axis: null,        // 'work' | 'taxonomy' | 'capabilities'
  dirty: false,
  saving: false,
  errors: [],        // validation error strings from server
  conflict: null,    // { type, local, server } -- 409 recovery state

  // Core edit (fields + body of an object)
  item: null,        // the selected item being edited
  payload: null,     // full API payload (with revision tokens)
  draft: { fields: {}, body: "" },
  original: { fields: {}, body: "" },
  revision: "",      // core revision token

  // Artifact / sidecar edit
  resourceSlug: null,
  resourceName: null,
  resourceDraft: "",
  resourceOriginal: "",
  resourceRevision: "",
  resourceMediaType: "text/markdown",
};

// ============================================================
// EDITOR REGISTRIES (field descriptors - extensible for Phase 4)
// ============================================================

/**
 * @typedef {Object} FieldDescriptor
 * @property {string} key    - API field name
 * @property {string} label  - Display label
 * @property {'text'|'number'|'select'} type
 * @property {string[]} [options] - For select: valid values (first empty = unset)
 */

const WORK_FIELD_DESCRIPTORS = [
  { key: "title", label: "Title", type: "text" },
  { key: "priority", label: "Priority", type: "number" },
  { key: "effort", label: "Effort", type: "select",
    options: ["", "low", "medium", "high", "very-high"] },
  { key: "complexity", label: "Complexity", type: "select",
    options: ["", "low", "medium", "high", "very-high"] },
  { key: "initiative", label: "Initiative", type: "text" },
  { key: "parent", label: "Parent", type: "text" },
];

// ============================================================
// DOM REFERENCES
// ============================================================

const listEl = document.querySelector("#list");
const detail = document.querySelector("#detail");
const summary = document.querySelector("#summary");
const filterEl = document.querySelector("#filter");
const listTitle = document.querySelector("#list-title");
const toast = document.querySelector("#toast");

// ============================================================
// UTILITIES
// ============================================================

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function meta(parts) {
  return parts.filter(Boolean).map(esc).join(" · ");
}

function showToast(message) {
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, 2800);
}

// ============================================================
// API HELPERS
// ============================================================

async function fetchJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(res.status + " " + res.statusText);
  return res.json();
}

/**
 * Send a PATCH request with JSON body.
 * Returns { ok, status, data, error }.
 */
async function apiPatch(path, body) {
  const res = await fetch(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  try {
    const data = await res.json();
    return { ok: res.ok, status: res.status, data, error: data.error };
  } catch {
    return { ok: res.ok, status: res.status, data: null, error: res.statusText };
  }
}

/**
 * Send a PUT request with JSON body.
 * Returns { ok, status, data, error }.
 */
async function apiPut(path, body) {
  const res = await fetch(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  try {
    const data = await res.json();
    return { ok: res.ok, status: res.status, data, error: data.error };
  } catch {
    return { ok: res.ok, status: res.status, data: null, error: res.statusText };
  }
}

// ============================================================
// MARKDOWN EDITOR WIDGET
// ============================================================

/**
 * Update the preview pane from markdown text.
 * @param {string} md - raw markdown text
 * @param {HTMLElement} previewEl - target preview container
 */
function updatePreview(md, previewEl) {
  try {
    previewEl.innerHTML = marked.parse(md || "");
  } catch (e) {
    previewEl.textContent = "Preview render error: " + e.message;
  }
}

// ============================================================
// EDITOR STATE MANAGEMENT
// ============================================================

/**
 * Set the dirty flag and update the UI indicator.
 */
function setDirty(dirty) {
  editor.dirty = dirty;
  updateDirtyUI();
}

/**
 * Update the dirty indicator dot in the editor header.
 */
function updateDirtyUI() {
  const dot = detail.querySelector("#dirtyDot");
  if (dot) dot.hidden = !editor.dirty;
}

/**
 * Ask the user whether to leave the editor when dirty.
 * Returns true if the user confirms (or is not dirty).
 */
function canLeaveEditor() {
  if (!editor.dirty) return true;
  return confirm("You have unsaved changes. Leave without saving?");
}

/**
 * Exit the editor (used by navigation guards after confirmation).
 */
function exitEditor() {
  editor.mode = null;
  editor.dirty = false;
  editor.errors = [];
  editor.conflict = null;
  editor.saving = false;
}

/**
 * Enter core edit mode for the currently selected work item.
 * Uses the cached payload from renderWork to avoid a round-trip.
 */
function enterEditMode() {
  const payload = state.cachedWorkDetail;
  if (!payload) {
    showToast("No detail loaded - select an item first");
    return;
  }
  const item = payload.item;
  editor.mode = "core";
  editor.axis = "work";
  editor.item = item;
  editor.payload = payload;
  editor.revision = payload.coreRevision;
  editor.original = {
    fields: {
      title: item.title || "",
      priority: item.priority != null ? item.priority : null,
      effort: item.effort || "",
      complexity: item.complexity || "",
      initiative: item.initiative || "",
      parent: item.parent || "",
    },
    body: item.body || "",
  };
  // Deep copy for draft
  editor.draft = {
    fields: Object.assign({}, editor.original.fields),
    body: editor.original.body,
  };
  editor.dirty = false;
  editor.saving = false;
  editor.errors = [];
  editor.conflict = null;
  render();
}

/**
 * Enter artifact edit mode. Fetches the artifact content from the API.
 */
async function enterArtifactEdit(slug, name) {
  editor.mode = "artifact";
  editor.axis = "work";
  editor.resourceSlug = slug;
  editor.resourceName = name;
  editor.saving = false;
  editor.errors = [];
  editor.conflict = null;
  editor.dirty = false;

  try {
    const data = await fetchJson(
      "/api/work/" + encodeURIComponent(slug) + "/artifacts/" + encodeURIComponent(name)
    );
    editor.resourceDraft = data.content;
    editor.resourceOriginal = data.content;
    editor.resourceRevision = data.revision;
    editor.resourceMediaType = data.mediaType || "text/markdown";
    render();
  } catch (err) {
    showToast("Failed to load artifact: " + err.message);
    editor.mode = null;
    render();
  }
}

// ============================================================
// SAVE OPERATIONS
// ============================================================

/**
 * Save core (fields + body) via PATCH.
 */
async function saveCore() {
  if (editor.saving) return;
  editor.saving = true;
  editor.errors = [];
  editor.conflict = null;
  render();

  const slug = editor.item.slug;

  // Build PATCH body - only send fields that changed
  const fields = {};
  for (const key in editor.draft.fields) {
    if (editor.draft.fields[key] !== editor.original.fields[key]) {
      fields[key] = editor.draft.fields[key];
    }
  }
  const bodyChanged = editor.draft.body !== editor.original.body;

  const saveBody = {
    revision: editor.revision,
    fields: fields,
  };
  if (bodyChanged) {
    saveBody.body = editor.draft.body;
  }

  try {
    const result = await apiPatch("/api/work/" + encodeURIComponent(slug), saveBody);

    if (result.ok) {
      showToast("Saved");
      editor.mode = null;
      editor.dirty = false;
      await load();
    } else if (result.status === 409) {
      // Stale revision - keep draft, fetch server version
      editor.conflict = { type: "core", local: JSON.parse(JSON.stringify(editor.draft)), server: null };
      try { editor.conflict.server = await fetchJson("/api/work/" + encodeURIComponent(slug)); } catch (_e) { /* unable to fetch */ }
      render();
    } else {
      editor.errors = [result.error || ("Save failed (" + result.status + ")")];
      render();
    }
  } catch (err) {
    showToast("Save error: " + err.message);
    render();
  } finally {
    editor.saving = false;
  }
}

/**
 * Save artifact via PUT.
 */
async function saveArtifact() {
  if (editor.saving) return;
  editor.saving = true;
  editor.errors = [];
  editor.conflict = null;
  render();

  const slug = editor.resourceSlug;
  const name = editor.resourceName;

  try {
    const result = await apiPut(
      "/api/work/" + encodeURIComponent(slug) + "/artifacts/" + encodeURIComponent(name),
      {
        name: name,
        content: editor.resourceDraft,
        mediaType: editor.resourceMediaType,
        revision: editor.resourceRevision,
      }
    );

    if (result.ok) {
      showToast("Artifact saved");
      editor.mode = null;
      editor.dirty = false;
      await load();
    } else if (result.status === 409) {
      editor.conflict = { type: "artifact", local: editor.resourceDraft, server: null };
      try {
        editor.conflict.server = await fetchJson(
          "/api/work/" + encodeURIComponent(slug) + "/artifacts/" + encodeURIComponent(name)
        );
      } catch (_e) { /* unable to fetch */ }
      render();
    } else {
      editor.errors = [result.error || ("Save failed (" + result.status + ")")];
      render();
    }
  } catch (err) {
    showToast("Save error: " + err.message);
    render();
  } finally {
    editor.saving = false;
  }
}

/**
 * Cancel edit - confirms if dirty, then exits.
 */
function cancelEdit() {
  if (editor.dirty) {
    if (!confirm("You have unsaved changes. Discard them?")) {
      return;
    }
  }
  editor.mode = null;
  editor.dirty = false;
  editor.errors = [];
  editor.conflict = null;
  render();
}

/**
 * Render the conflict banner HTML for the current conflict state.
 */
function renderConflictHtml() {
  const c = editor.conflict;
  if (!c) return "";

  let serverText = "(unable to fetch server version)";
  if (c.server) {
    if (c.type === "artifact" || c.type === "sidecar") {
      serverText = c.server.content || "(empty)";
    } else {
      const item = c.server.item;
      serverText = "Title: " + (item ? (item.title || "(none)") : "(none)");
      if (item && item.body) {
        const preview = item.body.length > 500 ? item.body.substring(0, 500) + "..." : item.body;
        serverText += "\nBody: " + preview;
      }
    }
  }

  const copyBtn = (c.type === "artifact" || c.type === "sidecar")
    ? '<button class="conflict-copy" type="button">Copy server to clipboard</button>'
    : "";

  return '<div class="conflict-banner">' +
    '<h3>! Concurrent modification detected</h3>' +
    "<p>This resource was modified by another editor since you started editing. " +
    "Your draft is preserved below.</p>" +
    '<div class="conflict-server">' + esc(serverText) + "</div>" +
    '<div class="conflict-actions">' +
    '<button class="conflict-refresh" type="button">Refresh (replace with server)</button>' +
    copyBtn +
    '<button class="conflict-discard" type="button">Discard (return to view)</button>' +
    "</div></div>";
}

/**
 * Wire event listeners for conflict banner buttons.
 */
function wireConflictBanner() {
  if (!editor.conflict) return;
  const banner = detail.querySelector(".conflict-banner");
  if (!banner) return;

  var refreshBtn = banner.querySelector(".conflict-refresh");
  if (refreshBtn) {
    refreshBtn.addEventListener("click", function () {
      if (editor.conflict.type === "artifact" || editor.conflict.type === "sidecar") {
        editor.resourceDraft = editor.conflict.server.content;
        editor.resourceRevision = editor.conflict.server.revision;
        editor.resourceOriginal = editor.conflict.server.content;
      } else {
        var s = editor.conflict.server;
        var item = s.item;
        editor.draft.fields = {
          title: item ? (item.title || "") : "",
          priority: item ? (item.priority != null ? item.priority : null) : null,
          effort: item ? (item.effort || "") : "",
          complexity: item ? (item.complexity || "") : "",
          initiative: item ? (item.initiative || "") : "",
          parent: item ? (item.parent || "") : "",
        };
        editor.draft.body = item ? (item.body || "") : "";
        editor.revision = s.coreRevision;
        editor.original = {
          fields: Object.assign({}, editor.draft.fields),
          body: editor.draft.body,
        };
      }
      editor.conflict = null;
      editor.dirty = false;
      render();
    });
  }

  var copyBtn = banner.querySelector(".conflict-copy");
  if (copyBtn) {
    copyBtn.addEventListener("click", function () {
      var text;
      if (editor.conflict.type === "artifact" || editor.conflict.type === "sidecar") {
        text = editor.conflict.server.content;
      } else {
        text = JSON.stringify(editor.conflict.server, null, 2);
      }
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function () {
          showToast("Server version copied to clipboard");
        }).catch(function () {
          showToast("Copy failed - select and copy manually");
        });
      } else {
        showToast("Clipboard API not available");
      }
    });
  }

  var discardBtn = banner.querySelector(".conflict-discard");
  if (discardBtn) {
    discardBtn.addEventListener("click", function () {
      editor.mode = null;
      editor.dirty = false;
      editor.conflict = null;
      render();
    });
  }
}

// ============================================================
// RENDERING - CORE
// ============================================================

function render() {
  document.querySelectorAll(".tab").forEach(function (tab) {
    tab.classList.toggle("active", tab.dataset.view === state.view);
  });
  listTitle.textContent = labels[state.view];
  var counts = state.data.work.length + " work · " +
    state.data.taxonomy.length + " taxonomy · " +
    state.data.capabilities.length + " capabilities";
  summary.textContent = counts;
  renderList();
  if (editor.mode) {
    renderEditor();
  } else {
    renderDetail();
  }
}

function renderEditor() {
  if (editor.mode === "core") {
    renderWorkEditor();
  } else if (editor.mode === "artifact") {
    renderArtifactEditor();
  } else if (editor.mode === "sidecar") {
    renderArtifactEditor(); // reuse artifact editor for sidecars
  }
}

// ============================================================
// RENDERING - LIST
// ============================================================

function currentItems() {
  var items = state.data[state.view] || [];
  if (!state.filter) return items;
  var q = state.filter.toLowerCase();
  return items.filter(function (item) { return JSON.stringify(item).toLowerCase().includes(q); });
}

function itemTitle(item) {
  if (state.view === "work") return item.title || item.slug;
  if (state.view === "taxonomy") return item.name || item.slug;
  return item.name || item.ref;
}

function itemKey(item) {
  if (state.view === "work") return item.slug;
  if (state.view === "taxonomy") return item.qualified || item.slug;
  return item.ref;
}

function itemMeta(item) {
  if (state.view === "work") {
    return meta([item.status, item.effort && ("effort " + item.effort), item.complexity && ("complexity " + item.complexity)]);
  }
  if (state.view === "taxonomy") {
    return meta([item.kind, item.origin, item.slug]);
  }
  return meta([item.status, item.file_id]);
}

function renderList() {
  var items = currentItems();
  if (!items.length) {
    listEl.innerHTML = '<p class="empty">No ' + esc(labels[state.view].toLowerCase()) + ' entries.</p>';
    return;
  }
  listEl.innerHTML = items.map(function (item) {
    var key = itemKey(item);
    var active = state.selected === key ? " active" : "";
    return '<button class="item' + active + '" type="button" data-key="' + esc(key) + '">' +
      '<div class="item-title">' + esc(itemTitle(item)) + "</div>" +
      '<div class="item-meta">' + itemMeta(item) + "</div></button>";
  }).join("");

  listEl.querySelectorAll(".item").forEach(function (button) {
    button.addEventListener("click", function () {
      if (editor.mode && !canLeaveEditor()) return;
      exitEditor();
      state.selected = button.dataset.key;
      render();
    });
  });
}

// ============================================================
// RENDERING - DETAIL
// ============================================================

function selectedItem() {
  var items = currentItems();
  if (!items.length) return null;
  return items.find(function (item) { return itemKey(item) === state.selected; }) || items[0];
}

function renderDetail() {
  var item = selectedItem();
  if (!item) {
    detail.innerHTML = '<p class="empty">Select an entry.</p>';
    return;
  }
  state.selected = itemKey(item);
  if (state.view === "work") {
    renderWork(item);
  } else if (state.view === "taxonomy") {
    renderTaxonomy(item);
  } else {
    renderCapability(item);
  }
}

function field(name, value) {
  return '<div class="field"><span>' + esc(name) + "</span>" + esc(value) + "</div>";
}

// ============================================================
// RENDERING - WORK DETAIL (with edit affordance)
// ============================================================

async function renderWork(item) {
  detail.innerHTML = '<p class="empty">Loading ' + esc(item.slug) + "...</p>";
  try {
    var payload = await fetchJson("/api/work/" + encodeURIComponent(item.slug));
    state.cachedWorkDetail = payload; // cache for editor
    var got = payload.item;
    var artifacts = payload.artifacts.filter(function (a) { return a.present && a.name !== "initial-request"; });

    var artifactHtml = artifacts.map(function (artifact) {
      var editBtn = artifact.present
        ? '<button class="artifact-edit" type="button" data-slug="' + esc(got.slug) +
          '" data-name="' + esc(artifact.name) +
          '" aria-label="Edit ' + esc(artifact.name) + '">&#9998;</button>'
        : "";
      return '<div class="artifact-group">' +
        '<button class="artifact" type="button" data-name="' + esc(artifact.name) + '">' +
        esc(artifact.name) + "</button>" + editBtn + "</div>";
    }).join("");

    detail.innerHTML =
      '<div class="detail-head">' +
        '<div>' +
          '<h2>' + esc(got.title || got.slug) + "</h2>" +
          '<p class="item-meta">' + esc(got.slug) + "</p>" +
        "</div>" +
        '<div class="detail-actions">' +
          '<span class="badge">' + esc(got.status) + "</span>" +
          '<button class="edit-btn" type="button">Edit</button>' +
        "</div>" +
      "</div>" +
      '<div class="fields">' +
        field("Priority", got.priority != null ? got.priority : "-") +
        field("Effort", got.effort || "-") +
        field("Complexity", got.complexity || "-") +
        field("Resolution", got.resolution || "-") +
      "</div>" +
      '<div class="artifacts">' + artifactHtml + "</div>" +
      '<article class="body">' + marked.parse(got.body || "") + "</article>";

    // Wire existing artifact open buttons
    detail.querySelectorAll(".artifact").forEach(function (button) {
      button.addEventListener("click", function () { openArtifact(got.slug, button.dataset.name); });
    });
    // Wire new artifact edit buttons
    detail.querySelectorAll(".artifact-edit").forEach(function (button) {
      button.addEventListener("click", function () {
        enterArtifactEdit(button.dataset.slug, button.dataset.name);
      });
    });
    // Wire core edit button
    var editBtn = detail.querySelector(".edit-btn");
    if (editBtn) {
      editBtn.addEventListener("click", function () { enterEditMode(); });
    }
  } catch (err) {
    detail.innerHTML = '<p class="empty">Failed to load work item: ' + esc(err.message) + "</p>";
  }
}

// ============================================================
// RENDERING - TAXONOMY DETAIL (unchanged)
// ============================================================

function renderTaxonomy(item) {
  detail.innerHTML =
    '<div class="detail-head">' +
      '<div>' +
        '<h2>' + esc(item.name) + "</h2>" +
        '<p class="item-meta">' + esc(item.qualified || item.slug) + "</p>" +
      "</div>" +
      '<span class="badge">' + esc(item.kind) + "</span>" +
    "</div>" +
    '<div class="fields">' +
      field("Origin", item.origin) +
      field("Relates to", (item.relates_to || []).join(", ") || "-") +
      field("Vocabulary", (item.vocabulary || []).join(", ") || "-") +
      field("Attachments", (item.attachments || []).join(", ") || "-") +
    "</div>" +
    '<article class="body">' + marked.parse(item.description || "") + "</article>";
}

// ============================================================
// RENDERING - CAPABILITY DETAIL (unchanged)
// ============================================================

function renderCapability(item) {
  var fields = item.fields || {};
  detail.innerHTML =
    '<div class="detail-head">' +
      '<div>' +
        '<h2>' + esc(item.name) + "</h2>" +
        '<p class="item-meta">' + esc(item.ref) + "</p>" +
      "</div>" +
      '<span class="badge">' + esc(fields.Status || "Unspecified") + "</span>" +
    "</div>" +
    '<div class="fields">' +
      Object.entries(fields).map(function (entry) { return field(entry[0], entry[1]); }).join("") +
    "</div>" +
    '<article class="body">' + marked.parse(item.body || "") + "</article>";
}

// ============================================================
// RENDERING - WORK EDITOR
// ============================================================

function renderWorkEditor() {
  var item = editor.item;
  var d = editor.draft;
  var savingClass = editor.saving ? " saving" : "";

  // Build field rows from descriptors
  var fieldRows = WORK_FIELD_DESCRIPTORS.map(function (desc) {
    var value = d.fields[desc.key];
    var inputHtml;
    if (desc.type === "select") {
      var options = (desc.options || []).map(function (opt) {
        var selected = (value === opt || (value === "" && opt === "")) ? " selected" : "";
        return '<option value="' + esc(opt) + '"' + selected + ">" + esc(opt || "(unset)") + "</option>";
      }).join("");
      inputHtml = '<select class="field-select" data-field="' + esc(desc.key) + '">' + options + "</select>";
    } else if (desc.type === "number") {
      var numVal = (value != null && value !== "") ? String(value) : "";
      inputHtml = '<input type="number" class="field-input" data-field="' + esc(desc.key) + '" value="' + esc(numVal) + '">';
    } else {
      inputHtml = '<input type="text" class="field-input" data-field="' + esc(desc.key) + '" value="' + esc(value || "") + '">';
    }
    return '<div class="field-group"><label>' + esc(desc.label) + "</label>" + inputHtml + "</div>";
  }).join("");

  var validationHtml = "";
  if (editor.errors.length > 0) {
    var errorItems = editor.errors.map(function (e) { return "<li>" + esc(e) + "</li>"; }).join("");
    validationHtml = '<div class="validation-errors"><strong>Validation errors</strong><ul>' + errorItems + "</ul></div>";
  }

  var conflictHtml = "";
  if (editor.conflict) {
    conflictHtml = renderConflictHtml();
  }

  var saveBtnText = editor.saving ? "Saving..." : "Save";

  detail.innerHTML =
    '<div class="editor-container' + savingClass + '">' +
      '<div class="editor-header">' +
        '<div class="editor-title">Edit: ' + esc(item.title || item.slug) +
          '<span class="dirty-dot" id="dirtyDot" hidden></span></div>' +
        '<div class="editor-actions">' +
          '<button class="cancel-btn" type="button">Cancel</button>' +
          '<button class="save-btn" type="button">' + saveBtnText + "</button>" +
        "</div>" +
      "</div>" +
      validationHtml + conflictHtml +
      '<div class="editor-section">Fields</div>' +
      '<div class="editor-fields">' + fieldRows + "</div>" +
      '<div class="editor-section">Body</div>' +
      '<div class="md-editor">' +
        '<textarea class="md-input" id="mdInput" placeholder="Write Markdown..."></textarea>' +
        '<div class="md-preview" id="mdPreview"></div>' +
      "</div>" +
    "</div>";

  // Set textarea value directly (not via innerHTML to avoid escaping)
  var mdInput = detail.querySelector("#mdInput");
  var mdPreview = detail.querySelector("#mdPreview");
  mdInput.value = d.body;
  updatePreview(d.body, mdPreview);

  // Wire save / cancel
  detail.querySelector(".save-btn").addEventListener("click", saveCore);
  detail.querySelector(".cancel-btn").addEventListener("click", cancelEdit);

  // Wire field inputs
  detail.querySelectorAll(".field-input, .field-select").forEach(function (el) {
    el.addEventListener("input", function () {
      var key = el.dataset.field;
      if (el.type === "number") {
        editor.draft.fields[key] = el.value === "" ? null : Number(el.value);
      } else {
        editor.draft.fields[key] = el.value;
      }
      setDirty(true);
    });
  });

  // Wire markdown editor live preview
  mdInput.addEventListener("input", function () {
    editor.draft.body = mdInput.value;
    updatePreview(mdInput.value, mdPreview);
    setDirty(true);
  });

  // Wire conflict banner buttons
  wireConflictBanner();

  // Update dirty indicator
  updateDirtyUI();
}

// ============================================================
// RENDERING - ARTIFACT EDITOR
// ============================================================

function renderArtifactEditor() {
  var name = editor.resourceName;
  var content = editor.resourceDraft;
  var savingClass = editor.saving ? " saving" : "";

  var validationHtml = "";
  if (editor.errors.length > 0) {
    var errorItems = editor.errors.map(function (e) { return "<li>" + esc(e) + "</li>"; }).join("");
    validationHtml = '<div class="validation-errors"><strong>Validation errors</strong><ul>' + errorItems + "</ul></div>";
  }

  var conflictHtml = "";
  if (editor.conflict) {
    conflictHtml = renderConflictHtml();
  }

  var saveBtnText = editor.saving ? "Saving..." : "Save";

  detail.innerHTML =
    '<div class="editor-container' + savingClass + '">' +
      '<div class="editor-header">' +
        '<div class="editor-title">Edit artifact: ' + esc(name) +
          '<span class="dirty-dot" id="dirtyDot" hidden></span></div>' +
        '<div class="editor-actions">' +
          '<button class="cancel-btn" type="button">Cancel</button>' +
          '<button class="save-btn" type="button">' + saveBtnText + "</button>" +
        "</div>" +
      "</div>" +
      validationHtml + conflictHtml +
      '<div class="md-editor">' +
        '<textarea class="md-input" id="mdInput" placeholder="Write Markdown..."></textarea>' +
        '<div class="md-preview" id="mdPreview"></div>' +
      "</div>" +
    "</div>";

  var mdInput = detail.querySelector("#mdInput");
  var mdPreview = detail.querySelector("#mdPreview");
  mdInput.value = content;
  updatePreview(content, mdPreview);

  detail.querySelector(".save-btn").addEventListener("click", saveArtifact);
  detail.querySelector(".cancel-btn").addEventListener("click", cancelEdit);

  mdInput.addEventListener("input", function () {
    editor.resourceDraft = mdInput.value;
    updatePreview(mdInput.value, mdPreview);
    setDirty(true);
  });

  wireConflictBanner();
  updateDirtyUI();
}

// ============================================================
// ARTIFACT OPEN (existing behavior, preserved)
// ============================================================

async function openArtifact(slug, name) {
  try {
    var res = await fetch(
      "/api/work/" + encodeURIComponent(slug) + "/artifacts/" + encodeURIComponent(name) + "/open",
      { method: "POST" }
    );
    if (!res.ok) throw new Error(res.status + " " + res.statusText);
    if (res.status === 204) {
      showToast("Opened artifact");
      return;
    }
    var payload = await res.json();
    if (payload.url) window.open(payload.url, "_blank", "noopener");
  } catch (err) {
    showToast("Could not open artifact: " + err.message);
  }
}

// ============================================================
// NAVIGATION GUARDS
// ============================================================

// Browser close / hard refresh guard
window.addEventListener("beforeunload", function (e) {
  if (editor.dirty) {
    e.preventDefault();
    e.returnValue = "";
  }
});

// ============================================================
// INITIALIZATION
// ============================================================

async function load() {
  try {
    var results = await Promise.all([
      fetchJson("/api/work"),
      fetchJson("/api/taxonomy"),
      fetchJson("/api/capabilities"),
    ]);
    state.data = { work: results[0], taxonomy: results[1], capabilities: results[2] };
    state.selected = null;
    render();
  } catch (err) {
    detail.innerHTML = '<p class="empty">Failed to load: ' + esc(err.message) +
      '</p><button class="retry" type="button">Retry</button>';
    detail.querySelector(".retry").addEventListener("click", load);
  }
}

// Tab clicks - with dirty guard
document.querySelectorAll(".tab").forEach(function (tab) {
  tab.addEventListener("click", function () {
    if (editor.mode && tab.dataset.view !== state.view) {
      if (!canLeaveEditor()) return;
      exitEditor();
    }
    state.view = tab.dataset.view;
    state.selected = null;
    render();
  });
});

// Filter input - with dirty guard
filterEl.addEventListener("input", function () {
  if (editor.mode) {
    if (!canLeaveEditor()) return;
    exitEditor();
  }
  state.filter = filterEl.value;
  state.selected = null;
  render();
});

load();
