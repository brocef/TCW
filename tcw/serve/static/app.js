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
// TODO (Phase 5): Verification, docs, capability flip

// ============================================================
// STATE
// ============================================================

// Work status vocabulary (mirrors WORK_STATUSES in tcw/store/base.py), in
// lifecycle order. Drives the status-filter toggle bar on the Work board.
const WORK_STATUSES = ["inbox", "backlog", "active", "completed"];

// Top-to-bottom grouping order for the work list (distinct from the lifecycle
// order above, which drives the status-filter toggles). Do not conflate the two.
const WORK_STATUS_GROUP_ORDER = ["active", "backlog", "inbox", "completed"];

const state = {
  view: "work",
  data: { work: [], taxonomy: [], capabilities: [] },
  selected: null,
  filter: "",
  // Which work statuses are visible; completed hidden by default. Derived from
  // WORK_STATUSES so the map can't drift from the toggle-button set.
  statusFilter: Object.fromEntries(WORK_STATUSES.map(function (s) { return [s, s !== "completed"]; })),
  cachedWorkDetail: null, // payload cached by renderWork for editor use
  cachedTaxonomyDetail: null,
  cachedCapabilityDetail: null,
  // Post-write warnings to show after reload
  postWarnings: null,
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
  mode: null,        // null | 'core' | 'artifact' | 'sidecar' | 'create'
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
  ref: "",           // taxonomy/capability ref for API URLs

  // Create mode
  createDraft: {},   // draft fields for create form

  // Artifact / sidecar edit
  resourceSlug: null,
  resourceName: null,
  resourceDraft: "",
  resourceOriginal: "",
  resourceRevision: "",
  resourceMediaType: "text/markdown",
};

// ============================================================
// EDITOR REGISTRIES (field descriptors)
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

const TAXONOMY_FIELD_DESCRIPTORS = [
  { key: "name", label: "Name", type: "text" },
  { key: "kind", label: "Kind", type: "select",
    options: ["", "Vocabulary", "Feature"] },
  { key: "slug", label: "Slug", type: "text" },
  { key: "parent", label: "Parent", type: "text" },
];

const CAPABILITY_FIELD_DESCRIPTORS = [
  { key: "Status", label: "Status", type: "select",
    options: ["", "Supported", "Partial", "Missing", "Blocked", "Omitted"] },
  { key: "Priority", label: "Priority", type: "select",
    options: ["", "P0", "P1", "P2", "P3"] },
  { key: "Lifecycle", label: "Lifecycle", type: "select",
    options: ["", "Experimental", "Stable", "Deprecated"] },
  { key: "Feature", label: "Feature", type: "text" },
  { key: "Subject", label: "Subject", type: "text" },
  { key: "Roles", label: "Roles", type: "text" },
  { key: "When", label: "When", type: "text" },
  { key: "Gaps", label: "Gaps", type: "text" },
  { key: "Blocked by", label: "Blocked by", type: "text" },
  { key: "Tracker", label: "Tracker", type: "text" },
  { key: "Planning doc", label: "Planning doc", type: "text" },
  { key: "Superseded by", label: "Superseded by", type: "text" },
];

// ============================================================
// DOM REFERENCES
// ============================================================

const listEl = document.querySelector("#list");
const detail = document.querySelector("#detail");
const summary = document.querySelector("#summary");
const filterEl = document.querySelector("#filter");
const listTitle = document.querySelector("#list-title");
const statusFiltersEl = document.querySelector("#status-filters");
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

/**
 * Send a POST request with JSON body.
 * Returns { ok, status, data, error }.
 */
async function apiPost(path, body) {
  const res = await fetch(path, {
    method: "POST",
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
 * Send a DELETE request with JSON content-type header (required by server).
 * Returns { ok, status, data, error }.
 */
async function apiDelete(path) {
  const res = await fetch(path, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });
  try {
    const data = await res.json();
    return { ok: res.ok, status: res.status, data, error: data.error };
  } catch {
    return { ok: res.ok, status: res.status, data: null, error: res.statusText };
  }
}

// ============================================================
// MODAL SYSTEM (in-page dialog, no alert/confirm/prompt)
// ============================================================

let _modalResolve = null; // promise resolver for modal dismissals

/**
 * Show a modal with the given content HTML.
 * Returns a Promise that resolves when the modal is dismissed (via data-action buttons).
 */
function showModal(title, contentHtml) {
  return new Promise(function (resolve) {
    _modalResolve = resolve;
    var overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML =
      '<div class="modal-box" style="position:relative">' +
        '<button class="modal-dismiss" type="button" aria-label="Close">&times;</button>' +
        '<h2>' + esc(title) + "</h2>" +
        contentHtml +
      "</div>";

    // Wire dismiss button
    var dismissBtn = overlay.querySelector(".modal-dismiss");
    dismissBtn.addEventListener("click", function () {
      overlay.remove();
      _modalResolve = null;
    });

    // Wire data-action buttons
    overlay.querySelectorAll("[data-action]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var action = btn.dataset.action;
        var result = btn.dataset.result ? JSON.parse(btn.dataset.result) : null;
        overlay.remove();
        var r = _modalResolve;
        _modalResolve = null;
        r({ action: action, result: result });
      });
    });

    // Close on overlay click (outside modal box)
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) {
        overlay.remove();
        var r = _modalResolve;
        _modalResolve = null;
        r({ action: "dismiss" });
      }
    });

    document.body.appendChild(overlay);
  });
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
  var dot = detail.querySelector("#dirtyDot");
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
  var payload = state.cachedWorkDetail;
  if (!payload) {
    showToast("No detail loaded - select an item first");
    return;
  }
  var item = payload.item;
  editor.mode = "core";
  editor.axis = "work";
  editor.item = item;
  editor.payload = payload;
  editor.revision = payload.coreRevision;
  editor.ref = item.slug;
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
  // Store blockers as a list of strings for the tag input
  editor.draft.blockers = (item.blocked_by || []).map(function (b) {
    return b.slug || b.external || "";
  }).filter(Boolean);
  editor.original.blockers = editor.draft.blockers.slice();
  editor.dirty = false;
  editor.saving = false;
  editor.errors = [];
  editor.conflict = null;
  render();
}

/**
 * Enter core edit mode for taxonomy term.
 */
function enterTaxonomyEdit() {
  var payload = state.cachedTaxonomyDetail;
  if (!payload) {
    showToast("No detail loaded");
    return;
  }
  var term = payload.term;
  editor.mode = "core";
  editor.axis = "taxonomy";
  editor.item = term;
  editor.payload = payload;
  editor.revision = payload.coreRevision;
  var qual = term.qualified || term.slug;
  editor.ref = qual;
  editor.original = {
    fields: {
      name: term.name || "",
      kind: term.kind || "Vocabulary",
      relates_to: term.relates_to || [],
      vocabulary: term.vocabulary || [],
    },
    body: term.description || "",
  };
  editor.draft = {
    fields: {
      name: term.name || "",
      kind: term.kind || "Vocabulary",
      relates_to: (term.relates_to || []).slice(),
      vocabulary: (term.vocabulary || []).slice(),
    },
    body: term.description || "",
  };
  editor.original.blockers = [];
  editor.draft.blockers = [];
  editor.dirty = false;
  editor.saving = false;
  editor.errors = [];
  editor.conflict = null;
  render();
}

/**
 * Enter core edit mode for capability.
 */
function enterCapabilityEdit() {
  var payload = state.cachedCapabilityDetail;
  if (!payload) {
    showToast("No detail loaded");
    return;
  }
  var cap = payload.capability;
  editor.mode = "core";
  editor.axis = "capabilities";
  editor.item = cap;
  editor.payload = payload;
  editor.revision = payload.coreRevision;
  editor.ref = cap.ref;
  var fields = cap.fields || {};
  editor.original = {
    fields: Object.assign({}, fields),
    body: cap.body || "",
  };
  editor.draft = {
    fields: Object.assign({}, fields),
    body: cap.body || "",
  };
  editor.original.blockers = [];
  editor.draft.blockers = [];
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
    var data = await fetchJson(
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

/**
 * Enter sidecar edit mode. Fetches the sidecar content from the API.
 */
async function enterSidecarEdit(slug, name) {
  editor.mode = "sidecar";
  editor.axis = "work";
  editor.resourceSlug = slug;
  editor.resourceName = name;
  editor.saving = false;
  editor.errors = [];
  editor.conflict = null;
  editor.dirty = false;

  try {
    var data = await fetchJson(
      "/api/work/" + encodeURIComponent(slug) + "/sidecars/" + encodeURIComponent(name)
    );
    editor.resourceDraft = data.content;
    editor.resourceOriginal = data.content;
    editor.resourceRevision = data.revision;
    editor.resourceMediaType = data.mediaType || "application/yaml";
    render();
  } catch (err) {
    showToast("Failed to load sidecar: " + err.message);
    editor.mode = null;
    render();
  }
}

// ============================================================
// SAVE OPERATIONS
// ============================================================

/**
 * Save core (fields + body) via PATCH.
 * Handles work, taxonomy, and capability axes.
 */
async function saveCore() {
  if (editor.saving) return;
  editor.saving = true;
  editor.errors = [];
  editor.conflict = null;
  render();

  var axis = editor.axis;

  if (axis === "work") {
    await _saveWorkCore();
  } else if (axis === "taxonomy") {
    await _saveTaxonomyCore();
  } else if (axis === "capabilities") {
    await _saveCapabilityCore();
  }

  editor.saving = false;
}

/**
 * Save work core via PATCH /api/work/<slug>.
 */
async function _saveWorkCore() {
  var slug = editor.item.slug;

  // Build PATCH body - only send fields that changed
  var fields = {};
  for (var key in editor.draft.fields) {
    if (editor.draft.fields[key] !== editor.original.fields[key]) {
      fields[key] = editor.draft.fields[key];
    }
  }
  // Blockers
  var draftBlockers = editor.draft.blockers || [];
  var origBlockers = editor.original.blockers || [];
  if (JSON.stringify(draftBlockers) !== JSON.stringify(origBlockers)) {
    // Send plain string refs; the store resolves each to {slug}/{external}.
    fields.blockers = draftBlockers.slice();
  }

  var bodyChanged = editor.draft.body !== editor.original.body;

  var saveBody = {
    revision: editor.revision,
    fields: fields,
  };
  if (bodyChanged) {
    saveBody.body = editor.draft.body;
  }

  try {
    var result = await apiPatch("/api/work/" + encodeURIComponent(slug), saveBody);

    if (result.ok) {
      // Check for warnings
      if (result.data.warnings && result.data.warnings.length > 0) {
        state.postWarnings = result.data.warnings;
      }
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
  }
}

/**
 * Save taxonomy core via PATCH /api/taxonomy/<ref>.
 */
async function _saveTaxonomyCore() {
  var ref = editor.ref;
  var encodedRef = encodeURIComponent(ref);

  // Build PATCH body
  var fields = {};
  var fieldMap = {
    name: "name",
    kind: "kind",
    relates_to: "relates_to",
    vocabulary: "vocabulary",
  };
  for (var draftKey in fieldMap) {
    var apiKey = fieldMap[draftKey];
    var draftVal = editor.draft.fields[draftKey];
    var origVal = editor.original.fields[draftKey];
    if (JSON.stringify(draftVal) !== JSON.stringify(origVal)) {
      fields[apiKey] = draftVal;
    }
  }

  var bodyChanged = editor.draft.body !== editor.original.body;

  var saveBody = {
    revision: editor.revision,
    fields: fields,
  };
  if (bodyChanged) {
    saveBody.body = editor.draft.body;
  }

  try {
    var result = await apiPatch("/api/taxonomy/" + encodedRef, saveBody);

    if (result.ok) {
      if (result.data.warnings && result.data.warnings.length > 0) {
        state.postWarnings = result.data.warnings;
      }
      showToast("Saved");
      editor.mode = null;
      editor.dirty = false;
      await load();
    } else if (result.status === 409) {
      editor.conflict = { type: "core", local: JSON.parse(JSON.stringify(editor.draft)), server: null };
      try { editor.conflict.server = await fetchJson("/api/taxonomy/" + encodedRef); } catch (_e) {}
      render();
    } else {
      editor.errors = [result.error || ("Save failed (" + result.status + ")")];
      render();
    }
  } catch (err) {
    showToast("Save error: " + err.message);
    render();
  }
}

/**
 * Save capability core via PATCH /api/capabilities/<ref>.
 */
async function _saveCapabilityCore() {
  var ref = editor.ref;
  var encodedRef = encodeURIComponent(ref);

  // Build PATCH body
  var fields = {};
  for (var key in editor.draft.fields) {
    if (editor.draft.fields[key] !== editor.original.fields[key]) {
      fields[key] = editor.draft.fields[key];
    }
  }

  var bodyChanged = editor.draft.body !== editor.original.body;

  var saveBody = {
    revision: editor.revision,
    fields: fields,
  };
  if (bodyChanged) {
    saveBody.body = editor.draft.body;
  }

  try {
    var result = await apiPatch("/api/capabilities/" + encodedRef, saveBody);

    if (result.ok) {
      if (result.data.warnings && result.data.warnings.length > 0) {
        state.postWarnings = result.data.warnings;
      }
      showToast("Saved");
      editor.mode = null;
      editor.dirty = false;
      await load();
    } else if (result.status === 409) {
      editor.conflict = { type: "core", local: JSON.parse(JSON.stringify(editor.draft)), server: null };
      try { editor.conflict.server = await fetchJson("/api/capabilities/" + encodedRef); } catch (_e) {}
      render();
    } else {
      editor.errors = [result.error || ("Save failed (" + result.status + ")")];
      render();
    }
  } catch (err) {
    showToast("Save error: " + err.message);
    render();
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

  var slug = editor.resourceSlug;
  var name = editor.resourceName;

  try {
    var result = await apiPut(
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
 * Save sidecar via PUT.
 */
async function saveSidecar() {
  if (editor.saving) return;
  editor.saving = true;
  editor.errors = [];
  editor.conflict = null;
  render();

  var slug = editor.resourceSlug;
  var name = editor.resourceName;

  try {
    var result = await apiPut(
      "/api/work/" + encodeURIComponent(slug) + "/sidecars/" + encodeURIComponent(name),
      {
        name: name,
        content: editor.resourceDraft,
        mediaType: editor.resourceMediaType,
        revision: editor.resourceRevision,
      }
    );

    if (result.ok) {
      showToast("Sidecar saved");
      editor.mode = null;
      editor.dirty = false;
      await load();
    } else if (result.status === 409) {
      editor.conflict = { type: "sidecar", local: editor.resourceDraft, server: null };
      try {
        editor.conflict.server = await fetchJson(
          "/api/work/" + encodeURIComponent(slug) + "/sidecars/" + encodeURIComponent(name)
        );
      } catch (_e) {}
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

// ============================================================
// CREATE OPERATIONS
// ============================================================

/**
 * Enter create mode for an axis.
 */
function enterCreate(axis) {
  editor.mode = "create";
  editor.axis = axis;
  editor.saving = false;
  editor.errors = [];
  editor.conflict = null;
  editor.dirty = false;

  if (axis === "work") {
    editor.createDraft = {
      title: "",
      priority: "",
      effort: "",
      complexity: "",
      blockers: [],
      parent: "",
      initiative: "",
      body: "",
    };
  } else if (axis === "taxonomy") {
    editor.createDraft = {
      name: "",
      kind: "Vocabulary",
      slug: "",
      parent: "",
      description: "",
      vocabulary: [],
    };
  } else if (axis === "capabilities") {
    editor.createDraft = {
      collection: "",
      name: "",
      status: "Missing",
      body: "",
    };
  }
  render();
}

/**
 * Save work create via POST /api/work.
 */
async function saveWorkCreate() {
  if (editor.saving) return;
  editor.saving = true;
  editor.errors = [];
  render();

  var d = editor.createDraft;
  // Prevalidate required title
  if (!d.title || !d.title.trim()) {
    editor.errors = ["Title is required"];
    editor.saving = false;
    render();
    return;
  }

  var body = {
    title: d.title.trim(),
  };
  if (d.priority !== "" && d.priority != null) body.priority = Number(d.priority);
  if (d.effort) body.effort = d.effort;
  if (d.complexity) body.complexity = d.complexity;
  if (d.parent && d.parent.trim()) body.parent = d.parent.trim();
  if (d.initiative && d.initiative.trim()) body.initiative = d.initiative.trim();
  var blockers = (d.blockers || []).filter(Boolean);
  if (blockers.length > 0) body.blockers = blockers;
  if (d.body) body.body = d.body;

  try {
    var result = await apiPost("/api/work", body);

    if (result.ok) {
      showToast("Work item created");
      editor.mode = null;
      editor.dirty = false;
      await load();
    } else {
      editor.errors = [result.error || ("Create failed (" + result.status + ")")];
      render();
    }
  } catch (err) {
    showToast("Create error: " + err.message);
    render();
  } finally {
    editor.saving = false;
  }
}

/**
 * Save taxonomy create via POST /api/taxonomy.
 */
async function saveTaxonomyCreate() {
  if (editor.saving) return;
  editor.saving = true;
  editor.errors = [];
  render();

  var d = editor.createDraft;
  if (!d.name || !d.name.trim()) {
    editor.errors = ["Name is required"];
    editor.saving = false;
    render();
    return;
  }

  var body = {
    name: d.name.trim(),
    kind: d.kind || "Vocabulary",
  };
  if (d.slug && d.slug.trim()) body.slug = d.slug.trim();
  if (d.parent && d.parent.trim()) body.parent = d.parent.trim();
  if (d.description) body.description = d.description;
  var vocab = (d.vocabulary || []).filter(Boolean);
  if (vocab.length > 0) body.vocabulary = vocab;

  try {
    var result = await apiPost("/api/taxonomy", body);

    if (result.ok) {
      if (result.data.warnings && result.data.warnings.length > 0) {
        state.postWarnings = result.data.warnings;
      }
      showToast("Term created");
      editor.mode = null;
      editor.dirty = false;
      await load();
    } else {
      editor.errors = [result.error || ("Create failed (" + result.status + ")")];
      render();
    }
  } catch (err) {
    showToast("Create error: " + err.message);
    render();
  } finally {
    editor.saving = false;
  }
}

/**
 * Save capability create via POST /api/capabilities.
 */
async function saveCapabilityCreate() {
  if (editor.saving) return;
  editor.saving = true;
  editor.errors = [];
  render();

  var d = editor.createDraft;
  if (!d.collection || !d.collection.trim()) {
    editor.errors = ["Collection is required"];
    editor.saving = false;
    render();
    return;
  }
  if (!d.name || !d.name.trim()) {
    editor.errors = ["Name is required"];
    editor.saving = false;
    render();
    return;
  }

  var body = {
    collection: d.collection.trim(),
    name: d.name.trim(),
    status: d.status || "Missing",
  };
  if (d.body) body.body = d.body;

  try {
    var result = await apiPost("/api/capabilities", body);

    if (result.ok) {
      if (result.data.warnings && result.data.warnings.length > 0) {
        state.postWarnings = result.data.warnings;
      }
      showToast("Capability created");
      editor.mode = null;
      editor.dirty = false;
      await load();
    } else {
      editor.errors = [result.error || ("Create failed (" + result.status + ")")];
      render();
    }
  } catch (err) {
    showToast("Create error: " + err.message);
    render();
  } finally {
    editor.saving = false;
  }
}

// ============================================================
// CONFLICT BANNER
// ============================================================

/**
 * Render the conflict banner HTML for the current conflict state.
 */
function renderConflictHtml() {
  var c = editor.conflict;
  if (!c) return "";

  var serverText = "(unable to fetch server version)";
  if (c.server) {
    if (c.type === "artifact" || c.type === "sidecar") {
      serverText = c.server.content || "(empty)";
    } else {
      var item = c.server.item || c.server.term || c.server.capability;
      serverText = "Title: " + (item ? (item.title || item.name || "(none)") : "(none)");
      if (item && (item.body || item.description)) {
        var preview = (item.body || item.description || "").length > 500
          ? (item.body || item.description).substring(0, 500) + "..."
          : (item.body || item.description);
        serverText += "\nBody: " + preview;
      }
    }
  }

  var copyBtn = (c.type === "artifact" || c.type === "sidecar")
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
  var banner = detail.querySelector(".conflict-banner");
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
        var item = s.item || s.term || s.capability;
        if (editor.axis === "work") {
          editor.draft.fields = {
            title: item ? (item.title || "") : "",
            priority: item ? (item.priority != null ? item.priority : null) : null,
            effort: item ? (item.effort || "") : "",
            complexity: item ? (item.complexity || "") : "",
            initiative: item ? (item.initiative || "") : "",
            parent: item ? (item.parent || "") : "",
          };
          editor.draft.body = item ? (item.body || "") : "";
          editor.draft.blockers = (item && item.blocked_by ? item.blocked_by.map(function(b){return b.slug||b.external||"";}).filter(Boolean) : []);
          editor.revision = s.coreRevision;
        } else if (editor.axis === "taxonomy") {
          editor.draft.fields = {
            name: item ? (item.name || "") : "",
            kind: item ? (item.kind || "Vocabulary") : "Vocabulary",
            relates_to: item ? (item.relates_to || []) : [],
            vocabulary: item ? (item.vocabulary || []) : [],
          };
          editor.draft.body = item ? (item.description || "") : "";
          editor.revision = s.coreRevision;
        } else if (editor.axis === "capabilities") {
          editor.draft.fields = item ? Object.assign({}, item.fields || {}) : {};
          editor.draft.body = item ? (item.body || "") : "";
          editor.revision = s.coreRevision;
        }
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
  var counts = state.data.taxonomy.length + " taxonomy · " +
    state.data.capabilities.length + " capabilities · " +
    state.data.work.length + " work items";
  summary.textContent = counts;
  renderStatusFilters();
  renderList();
  if (editor.mode) {
    renderEditor();
  } else {
    renderDetail();
  }
}

function renderEditor() {
  if (editor.mode === "create") {
    if (editor.axis === "work") renderWorkCreate();
    else if (editor.axis === "taxonomy") renderTaxonomyCreate();
    else if (editor.axis === "capabilities") renderCapabilityCreate();
  } else if (editor.mode === "core") {
    if (editor.axis === "work") renderWorkEditor();
    else if (editor.axis === "taxonomy") renderTaxonomyEditor();
    else if (editor.axis === "capabilities") renderCapabilityEditor();
  } else if (editor.mode === "artifact") {
    renderArtifactEditor();
  } else if (editor.mode === "sidecar") {
    renderSidecarEditor();
  }
}

// ============================================================
// RENDERING - LIST
// ============================================================

function currentItems() {
  var items = state.data[state.view] || [];
  if (state.view === "work") {
    // Hide a status only when its toggle is explicitly off; unknown statuses stay.
    items = items.filter(function (item) { return state.statusFilter[item.status] !== false; });
  }
  if (!state.filter) return items;
  var q = state.filter.toLowerCase();
  return items.filter(function (item) { return JSON.stringify(item).toLowerCase().includes(q); });
}

// Toggle bar above the work list: one button per status, on = visible. Work view
// only (statuses are a work concept); re-renders on toggle.
function renderStatusFilters() {
  if (state.view !== "work") {
    statusFiltersEl.hidden = true;
    statusFiltersEl.innerHTML = "";
    return;
  }
  statusFiltersEl.hidden = false;
  statusFiltersEl.innerHTML = WORK_STATUSES.map(function (s) {
    var on = state.statusFilter[s] !== false;
    return '<button type="button" class="status-toggle st-' + esc(s) + (on ? " on" : "") +
      '" data-status="' + esc(s) + '" aria-pressed="' + on + '">' + esc(s) + "</button>";
  }).join("");
  statusFiltersEl.querySelectorAll(".status-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var s = btn.dataset.status;
      state.statusFilter[s] = !state.statusFilter[s];  // flip (always a defined bool)
      render();
    });
  });
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
    var badge = '<span class="status-badge st-' + esc(item.status) + '">' + esc(item.status) + "</span>";
    var extra = meta([item.effort && ("effort " + item.effort), item.complexity && ("complexity " + item.complexity)]);
    return badge + (extra ? " " + extra : "");
  }
  if (state.view === "taxonomy") {
    return meta([item.kind, item.origin, item.slug]);
  }
  return meta([item.status, item.file_id]);
}

// One list row. Work rows are wrapped so a copy-slug button can sit beside the
// (full-width) item button — a button can't nest inside another button.
function itemRowHtml(item) {
  var key = itemKey(item);
  var active = state.selected === key ? " active" : "";
  var btn = '<button class="item' + active + '" type="button" data-key="' + esc(key) + '">' +
    '<div class="item-title">' + esc(itemTitle(item)) + "</div>" +
    '<div class="item-meta">' + itemMeta(item) + "</div></button>";
  if (state.view !== "work") return btn;
  var copyBtn = '<button class="copy-slug" type="button" data-slug="' + esc(key) +
    '" title="Copy slug" aria-label="Copy slug to clipboard">&#9112;</button>';
  return '<div class="item-row">' + btn + copyBtn + "</div>";
}

// Work list grouped under status headers in WORK_STATUS_GROUP_ORDER; empty groups
// are skipped; unknown statuses (shouldn't occur) fall after the known ones.
function groupedWorkHtml(items) {
  var order = WORK_STATUS_GROUP_ORDER.slice();
  var seen = {};
  order.forEach(function (s) { seen[s] = true; });
  items.forEach(function (it) {
    if (!seen[it.status]) { order.push(it.status); seen[it.status] = true; }
  });
  return order.map(function (status) {
    var group = items.filter(function (it) { return it.status === status; });
    if (!group.length) return "";
    return '<div class="status-group">' + esc(status) + "</div>" +
      group.map(itemRowHtml).join("");
  }).join("");
}

function renderList() {
  var items = currentItems();
  var createHtml = '<button class="create-btn" type="button">+ Create ' + esc(labels[state.view]) + "</button>";

  if (!items.length) {
    listEl.innerHTML =
      '<p class="empty">No ' + esc(labels[state.view].toLowerCase()) + ' entries.</p>' +
      createHtml;
  } else {
    var listHtml = state.view === "work"
      ? groupedWorkHtml(items)
      : items.map(itemRowHtml).join("");
    listEl.innerHTML = listHtml + createHtml;
  }

  listEl.querySelectorAll(".item").forEach(function (button) {
    button.addEventListener("click", function () {
      if (editor.mode && !canLeaveEditor()) return;
      exitEditor();
      state.selected = button.dataset.key;
      render();
    });
  });

  // Copy-slug buttons (work view). Sibling of .item, so it won't select the row.
  listEl.querySelectorAll(".copy-slug").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var slug = btn.dataset.slug;
      navigator.clipboard.writeText(slug).then(function () {
        showToast("Copied: " + slug);
      }).catch(function () {
        showToast("Copy failed");
      });
    });
  });

  // Wire create button
  var createBtn = listEl.querySelector(".create-btn");
  if (createBtn) {
    createBtn.addEventListener("click", function () {
      if (editor.mode && !canLeaveEditor()) return;
      exitEditor();
      state.selected = null;
      enterCreate(state.view);
    });
  }
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
  // Show post-write warnings if any
  var warningsHtml = "";
  if (state.postWarnings && state.postWarnings.length > 0) {
    var items = state.postWarnings.map(function (w) { return "<li>" + esc(w) + "</li>"; }).join("");
    warningsHtml = '<div class="warnings-banner"><strong>Warnings</strong><ul>' + items + "</ul></div>";
    state.postWarnings = null; // clear after render
  }

  var item = selectedItem();
  if (!item) {
    detail.innerHTML = warningsHtml + '<p class="empty">Select an entry.</p>';
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
// RENDERING - WORK DETAIL (with edit affordance + lifecycle + sidecars)
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

    // Sidecars section
    var sidecarsHtml = "";
    if (payload.sidecars && payload.sidecars.length > 0) {
      var sidecarItems = payload.sidecars.filter(function (s) { return s.present; }).map(function (sc) {
        return '<div class="sidecar-item">' +
          '<span class="sidecar-name">' + esc(sc.name) + "</span>" +
          '<button class="sidecar-edit-btn" type="button" data-slug="' + esc(got.slug) +
          '" data-name="' + esc(sc.name) + '">Edit</button></div>';
      }).join("");
      sidecarsHtml = '<div class="sidecars-section"><h3>Sidecars</h3>' + sidecarItems + "</div>";
    }

    // Lifecycle action buttons
    var actionsHtml = '<div class="action-buttons">';
    var status = got.status;
    if (status === "inbox" || status === "backlog") {
      actionsHtml += '<button class="action-btn start" type="button" data-action="start">Start</button>';
      actionsHtml += '<button class="action-btn drop" type="button" data-action="drop">Drop</button>';
    } else if (status === "active") {
      actionsHtml += '<button class="action-btn complete" type="button" data-action="complete">Complete</button>';
    }
    actionsHtml += "</div>";

    // Blockers display
    var blockersHtml = "";
    var blockedBy = got.blocked_by || [];
    if (blockedBy.length > 0) {
      var blockerLabels = blockedBy.map(function (b) {
        return b.slug ? esc(b.slug) : esc(b.external);
      }).join(", ");
      blockersHtml = field("Blocked by", blockerLabels);
    }

    // Parent / Initiative display
    var extraFields = "";
    if (got.parent) extraFields += field("Parent", got.parent);
    if (got.initiative) extraFields += field("Initiative", got.initiative);

    detail.innerHTML =
      warningsBannerHtml() +
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
      actionsHtml +
      '<div class="fields">' +
        field("Priority", got.priority != null ? got.priority : "-") +
        field("Effort", got.effort || "-") +
        field("Complexity", got.complexity || "-") +
        field("Resolution", got.resolution || "-") +
        blockersHtml + extraFields +
      "</div>" +
      '<div class="artifacts">' + artifactHtml + "</div>" +
      sidecarsHtml +
      '<article class="body">' + marked.parse(got.body || "") + "</article>";

    // Wire artifact open buttons
    detail.querySelectorAll(".artifact").forEach(function (button) {
      button.addEventListener("click", function () { openArtifact(got.slug, button.dataset.name); });
    });
    // Wire artifact edit buttons
    detail.querySelectorAll(".artifact-edit").forEach(function (button) {
      button.addEventListener("click", function () {
        enterArtifactEdit(button.dataset.slug, button.dataset.name);
      });
    });
    // Wire sidecar edit buttons
    detail.querySelectorAll(".sidecar-edit-btn").forEach(function (button) {
      button.addEventListener("click", function () {
        enterSidecarEdit(button.dataset.slug, button.dataset.name);
      });
    });
    // Wire core edit button
    var editBtn = detail.querySelector(".edit-btn");
    if (editBtn) {
      editBtn.addEventListener("click", function () { enterEditMode(); });
    }
    // Wire lifecycle action buttons
    detail.querySelectorAll(".action-btn").forEach(function (button) {
      button.addEventListener("click", function () {
        handleWorkAction(button.dataset.action, got.slug, got);
      });
    });
  } catch (err) {
    detail.innerHTML = '<p class="empty">Failed to load work item: ' + esc(err.message) + "</p>";
  }
}

/**
 * Render warnings banner HTML (for post-write warnings shown in detail).
 */
function warningsBannerHtml() {
  if (state.postWarnings && state.postWarnings.length > 0) {
    var items = state.postWarnings.map(function (w) { return "<li>" + esc(w) + "</li>"; }).join("");
    return '<div class="warnings-banner"><strong>Warnings</strong><ul>' + items + "</ul></div>";
  }
  return "";
}

/**
 * Handle work lifecycle actions (start, complete, drop).
 */
async function handleWorkAction(action, slug, item) {
  if (action === "start") {
    await handleStartAction(slug);
  } else if (action === "complete") {
    await showCompleteModal(slug, item);
  } else if (action === "drop") {
    await showDropModal(slug, item);
  }
}

/**
 * Show the drop confirmation modal.
 */
async function showDropModal(slug, item) {
  var result = await showModal("Drop Work Item",
    '<p>Are you sure you want to drop "' + esc(item.title || slug) + '"?</p>' +
    '<p style="color:var(--muted);font-size:13px">This will permanently delete the work item.</p>' +
    '<div class="modal-actions">' +
      '<button class="cancel-btn" type="button" data-action="dismiss">Cancel</button>' +
      '<button class="action-btn drop" type="button" data-action="drop">Drop</button>' +
    '</div>'
  );

  if (result && result.action === "drop") {
    var res = await apiDelete("/api/work/" + encodeURIComponent(slug));
    if (res.ok) {
      showToast("Work item dropped");
      exitEditor();
      state.selected = null;
      await load();
    } else {
      showToast(res.error || ("Drop failed (" + res.status + ")"));
    }
  }
}

// ============================================================
// RENDERING - TAXONOMY DETAIL (async, with edit)
// ============================================================

async function renderTaxonomy(item) {
  detail.innerHTML = '<p class="empty">Loading ' + esc(item.name) + "...</p>";
  try {
    var qual = item.qualified || item.slug;
    var encodedRef = encodeURIComponent(qual);
    var payload = await fetchJson("/api/taxonomy/" + encodedRef);
    state.cachedTaxonomyDetail = payload;
    var term = payload.term;

    detail.innerHTML = warningsBannerHtml() +
      '<div class="detail-head">' +
        '<div>' +
          '<h2>' + esc(term.name) + "</h2>" +
          '<p class="item-meta">' + esc(term.qualified || term.slug) + "</p>" +
        "</div>" +
        '<div class="detail-actions">' +
          '<span class="badge">' + esc(term.kind) + "</span>" +
          '<button class="edit-btn" type="button">Edit</button>' +
        "</div>" +
      "</div>" +
      '<div class="fields">' +
        field("Origin", term.origin) +
        field("Relates to", (term.relates_to || []).join(", ") || "-") +
        field("Vocabulary", (term.vocabulary || []).join(", ") || "-") +
        field("Attachments", (term.attachments || []).join(", ") || "-") +
      "</div>" +
      '<article class="body">' + marked.parse(term.description || "") + "</article>";

    var editBtn = detail.querySelector(".edit-btn");
    if (editBtn) {
      editBtn.addEventListener("click", function () { enterTaxonomyEdit(); });
    }
  } catch (err) {
    detail.innerHTML = '<p class="empty">Failed to load term: ' + esc(err.message) + "</p>";
  }
}

// ============================================================
// RENDERING - CAPABILITY DETAIL (async, with edit)
// ============================================================

async function renderCapability(item) {
  detail.innerHTML = '<p class="empty">Loading ' + esc(item.name) + "...</p>";
  try {
    var encodedRef = encodeURIComponent(item.ref);
    var payload = await fetchJson("/api/capabilities/" + encodedRef);
    state.cachedCapabilityDetail = payload;
    var cap = payload.capability;
    var fields = cap.fields || {};

    detail.innerHTML = warningsBannerHtml() +
      '<div class="detail-head">' +
        '<div>' +
          '<h2>' + esc(cap.name) + "</h2>" +
          '<p class="item-meta">' + esc(cap.ref) + "</p>" +
        "</div>" +
        '<div class="detail-actions">' +
          '<span class="badge">' + esc(fields.Status || "Unspecified") + "</span>" +
          '<button class="edit-btn" type="button">Edit</button>' +
        "</div>" +
      "</div>" +
      '<div class="fields">' +
        Object.entries(fields).map(function (entry) { return field(entry[0], entry[1]); }).join("") +
      "</div>" +
      '<article class="body">' + marked.parse(cap.body || "") + "</article>";

    var editBtn = detail.querySelector(".edit-btn");
    if (editBtn) {
      editBtn.addEventListener("click", function () { enterCapabilityEdit(); });
    }
  } catch (err) {
    detail.innerHTML = '<p class="empty">Failed to load capability: ' + esc(err.message) + "</p>";
  }
}

// ============================================================
// RENDERING - WORK EDITOR (extended with blockers + actions context)
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

  // Blocker tag input
  var blockers = d.blockers || [];
  var tagHtml = blockers.map(function (b, i) {
    return '<span class="blocker-tag">' + esc(b) +
      '<button type="button" class="remove-blocker" data-index="' + i + '">&times;</button></span>';
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
      '<div class="editor-section">Blocked by</div>' +
      '<div class="field-group">' +
        '<label>Add blocker (slug or external ref, press Enter)</label>' +
        '<input type="text" class="field-input" id="blockerInput" placeholder="e.g. other-item or EXT-123">' +
        '<div class="blocker-tags">' + tagHtml + '</div>' +
      '</div>' +
      '<div class="editor-section">Body</div>' +
      '<div class="md-editor">' +
        '<textarea class="md-input" id="mdInput" placeholder="Write Markdown..."></textarea>' +
        '<div class="md-preview" id="mdPreview"></div>' +
      "</div>" +
    "</div>";

  // Set textarea value directly
  var mdInput = detail.querySelector("#mdInput");
  var mdPreview = detail.querySelector("#mdPreview");
  mdInput.value = d.body;
  updatePreview(d.body, mdPreview);

  // Wire save / cancel
  detail.querySelector(".save-btn").addEventListener("click", saveCore);
  detail.querySelector(".cancel-btn").addEventListener("click", cancelEdit);

  // Wire field inputs
  detail.querySelectorAll(".field-input, .field-select").forEach(function (el) {
    if (el.id === "blockerInput") return; // skip blocker input
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

  // Wire blocker input (Enter to add)
  var blockerInput = detail.querySelector("#blockerInput");
  if (blockerInput) {
    blockerInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        var val = blockerInput.value.trim();
        if (val) {
          if (!editor.draft.blockers) editor.draft.blockers = [];
          editor.draft.blockers.push(val);
          blockerInput.value = "";
          setDirty(true);
          render();
        }
      }
    });
  }

  // Wire remove blocker buttons
  detail.querySelectorAll(".remove-blocker").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var idx = parseInt(btn.dataset.index, 10);
      editor.draft.blockers.splice(idx, 1);
      setDirty(true);
      render();
    });
  });

  // Wire markdown editor live preview
  mdInput.addEventListener("input", function () {
    editor.draft.body = mdInput.value;
    updatePreview(mdInput.value, mdPreview);
    setDirty(true);
  });

  wireConflictBanner();
  updateDirtyUI();
}

// ============================================================
// RENDERING - TAXONOMY EDITOR
// ============================================================

function renderTaxonomyEditor() {
  var term = editor.item;
  var d = editor.draft;
  var savingClass = editor.saving ? " saving" : "";

  // Build field rows
  var fieldRows = TAXONOMY_FIELD_DESCRIPTORS.map(function (desc) {
    var value = d.fields[desc.key];
    var inputHtml;
    if (desc.type === "select") {
      var options = (desc.options || []).map(function (opt) {
        var selected = (value === opt) ? " selected" : "";
        return '<option value="' + esc(opt) + '"' + selected + ">" + esc(opt) + "</option>";
      }).join("");
      inputHtml = '<select class="field-select" data-field="' + esc(desc.key) + '">' + options + "</select>";
    } else {
      inputHtml = '<input type="text" class="field-input" data-field="' + esc(desc.key) + '" value="' + esc(value || "") + '">';
    }
    return '<div class="field-group"><label>' + esc(desc.label) + "</label>" + inputHtml + "</div>";
  }).join("");

  // Relates to tag input
  var relatesTags = (d.fields.relates_to || []).map(function (r, i) {
    return '<span class="blocker-tag">' + esc(r) +
      '<button type="button" class="remove-tag" data-field="relates_to" data-index="' + i + '">&times;</button></span>';
  }).join("");

  // Vocabulary tag input
  var vocabTags = (d.fields.vocabulary || []).map(function (v, i) {
    return '<span class="blocker-tag">' + esc(v) +
      '<button type="button" class="remove-tag" data-field="vocabulary" data-index="' + i + '">&times;</button></span>';
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
        '<div class="editor-title">Edit term: ' + esc(term.name) +
          '<span class="dirty-dot" id="dirtyDot" hidden></span></div>' +
        '<div class="editor-actions">' +
          '<button class="cancel-btn" type="button">Cancel</button>' +
          '<button class="save-btn" type="button">' + saveBtnText + "</button>" +
        "</div>" +
      "</div>" +
      validationHtml + conflictHtml +
      '<div class="editor-section">Fields</div>' +
      '<div class="editor-fields">' + fieldRows + "</div>" +
      '<div class="editor-section">Relates to</div>' +
      '<div class="field-group">' +
        '<label>Add relation (press Enter)</label>' +
        '<input type="text" class="field-input" id="relatesInput" placeholder="term slug">' +
        '<div class="blocker-tags">' + relatesTags + '</div>' +
      '</div>' +
      '<div class="editor-section">Vocabulary (Feature refs)</div>' +
      '<div class="field-group">' +
        '<label>Add vocabulary ref (press Enter)</label>' +
        '<input type="text" class="field-input" id="vocabInput" placeholder="vocabulary term slug">' +
        '<div class="blocker-tags">' + vocabTags + '</div>' +
      '</div>' +
      '<div class="editor-section">Description</div>' +
      '<div class="md-editor">' +
        '<textarea class="md-input" id="mdInput" placeholder="Write Markdown..."></textarea>' +
        '<div class="md-preview" id="mdPreview"></div>' +
      "</div>" +
    "</div>";

  var mdInput = detail.querySelector("#mdInput");
  var mdPreview = detail.querySelector("#mdPreview");
  mdInput.value = d.body;
  updatePreview(d.body, mdPreview);

  detail.querySelector(".save-btn").addEventListener("click", saveCore);
  detail.querySelector(".cancel-btn").addEventListener("click", cancelEdit);

  // Wire field inputs
  detail.querySelectorAll(".field-input, .field-select").forEach(function (el) {
    if (el.id === "relatesInput" || el.id === "vocabInput") return;
    el.addEventListener("input", function () {
      var key = el.dataset.field;
      editor.draft.fields[key] = el.value;
      setDirty(true);
    });
  });

  // Wire relates_to input
  var relatesInput = detail.querySelector("#relatesInput");
  if (relatesInput) {
    relatesInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        var val = relatesInput.value.trim();
        if (val) {
          if (!editor.draft.fields.relates_to) editor.draft.fields.relates_to = [];
          editor.draft.fields.relates_to.push(val);
          relatesInput.value = "";
          setDirty(true);
          render();
        }
      }
    });
  }

  // Wire vocabulary input
  var vocabInput = detail.querySelector("#vocabInput");
  if (vocabInput) {
    vocabInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        var val = vocabInput.value.trim();
        if (val) {
          if (!editor.draft.fields.vocabulary) editor.draft.fields.vocabulary = [];
          editor.draft.fields.vocabulary.push(val);
          vocabInput.value = "";
          setDirty(true);
          render();
        }
      }
    });
  }

  // Wire remove tag buttons
  detail.querySelectorAll(".remove-tag").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var f = btn.dataset.field;
      var idx = parseInt(btn.dataset.index, 10);
      editor.draft.fields[f].splice(idx, 1);
      setDirty(true);
      render();
    });
  });

  mdInput.addEventListener("input", function () {
    editor.draft.body = mdInput.value;
    updatePreview(mdInput.value, mdPreview);
    setDirty(true);
  });

  wireConflictBanner();
  updateDirtyUI();
}

// ============================================================
// RENDERING - CAPABILITY EDITOR
// ============================================================

function renderCapabilityEditor() {
  var cap = editor.item;
  var d = editor.draft;
  var savingClass = editor.saving ? " saving" : "";

  // Build field rows
  var fieldRows = CAPABILITY_FIELD_DESCRIPTORS.map(function (desc) {
    var value = d.fields[desc.key] || "";
    var inputHtml;
    if (desc.type === "select") {
      var options = (desc.options || []).map(function (opt) {
        var selected = (value === opt || (value === "" && opt === "")) ? " selected" : "";
        return '<option value="' + esc(opt) + '"' + selected + ">" + esc(opt || "(unset)") + "</option>";
      }).join("");
      inputHtml = '<select class="field-select" data-field="' + esc(desc.key) + '">' + options + "</select>";
    } else {
      inputHtml = '<input type="text" class="field-input" data-field="' + esc(desc.key) + '" value="' + esc(value) + '">';
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
        '<div class="editor-title">Edit capability: ' + esc(cap.name) +
          '<span class="dirty-dot" id="dirtyDot" hidden></span></div>' +
        '<div class="editor-actions">' +
          '<button class="cancel-btn" type="button">Cancel</button>' +
          '<button class="save-btn" type="button">' + saveBtnText + "</button>" +
        "</div>" +
      "</div>" +
      validationHtml + conflictHtml +
      '<div class="editor-section">Metadata</div>' +
      '<div class="editor-fields">' + fieldRows + "</div>" +
      '<div class="editor-section">Body</div>' +
      '<div class="md-editor">' +
        '<textarea class="md-input" id="mdInput" placeholder="Write Markdown..."></textarea>' +
        '<div class="md-preview" id="mdPreview"></div>' +
      "</div>" +
    "</div>";

  var mdInput = detail.querySelector("#mdInput");
  var mdPreview = detail.querySelector("#mdPreview");
  mdInput.value = d.body;
  updatePreview(d.body, mdPreview);

  detail.querySelector(".save-btn").addEventListener("click", saveCore);
  detail.querySelector(".cancel-btn").addEventListener("click", cancelEdit);

  detail.querySelectorAll(".field-input, .field-select").forEach(function (el) {
    el.addEventListener("input", function () {
      var key = el.dataset.field;
      editor.draft.fields[key] = el.value;
      setDirty(true);
    });
  });

  mdInput.addEventListener("input", function () {
    editor.draft.body = mdInput.value;
    updatePreview(mdInput.value, mdPreview);
    setDirty(true);
  });

  wireConflictBanner();
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
// RENDERING - SIDECAR EDITOR (raw textarea, no Markdown preview)
// ============================================================

function renderSidecarEditor() {
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
  var mediaLabel = editor.resourceMediaType === "application/yaml" ? "YAML" : editor.resourceMediaType;

  detail.innerHTML =
    '<div class="editor-container' + savingClass + '">' +
      '<div class="editor-header">' +
        '<div class="editor-title">Edit sidecar: ' + esc(name) + " (" + esc(mediaLabel) + ")" +
          '<span class="dirty-dot" id="dirtyDot" hidden></span></div>' +
        '<div class="editor-actions">' +
          '<button class="cancel-btn" type="button">Cancel</button>' +
          '<button class="save-btn" type="button">' + saveBtnText + "</button>" +
        "</div>" +
      "</div>" +
      validationHtml + conflictHtml +
      '<div class="editor-section">Raw ' + esc(mediaLabel) + ' Content</div>' +
      '<div class="raw-editor">' +
        '<textarea class="raw-input" id="rawInput" placeholder="Edit raw content..."></textarea>' +
      "</div>" +
    "</div>";

  var rawInput = detail.querySelector("#rawInput");
  rawInput.value = content;

  detail.querySelector(".save-btn").addEventListener("click", saveSidecar);
  detail.querySelector(".cancel-btn").addEventListener("click", cancelEdit);

  rawInput.addEventListener("input", function () {
    editor.resourceDraft = rawInput.value;
    setDirty(true);
  });

  wireConflictBanner();
  updateDirtyUI();
}

// ============================================================
// RENDERING - CREATE FORMS
// ============================================================

function renderWorkCreate() {
  var d = editor.createDraft;
  var savingClass = editor.saving ? " saving" : "";

  // Build field rows
  var fieldRows = WORK_FIELD_DESCRIPTORS.map(function (desc) {
    var value = d[desc.key];
    var inputHtml;
    if (desc.type === "select") {
      var options = (desc.options || []).map(function (opt) {
        var selected = (value === opt || (value === "" && opt === "")) ? " selected" : "";
        return '<option value="' + esc(opt) + '"' + selected + ">" + esc(opt || "(unset)") + "</option>";
      }).join("");
      inputHtml = '<select class="field-select" data-create-field="' + esc(desc.key) + '">' + options + "</select>";
    } else if (desc.type === "number") {
      var numVal = (value != null && value !== "") ? String(value) : "";
      inputHtml = '<input type="number" class="field-input" data-create-field="' + esc(desc.key) + '" value="' + esc(numVal) + '">';
    } else {
      inputHtml = '<input type="text" class="field-input" data-create-field="' + esc(desc.key) + '" value="' + esc(value || "") + '">';
    }
    return '<div class="field-group"><label>' + esc(desc.label) + (desc.key === "title" ? " *" : "") + "</label>" + inputHtml + "</div>";
  }).join("");

  // Blocker tag display for create
  var blockers = d.blockers || [];
  var tagHtml = blockers.map(function (b, i) {
    return '<span class="blocker-tag">' + esc(b) +
      '<button type="button" class="remove-blocker" data-index="' + i + '">&times;</button></span>';
  }).join("");

  var validationHtml = "";
  if (editor.errors.length > 0) {
    var errorItems = editor.errors.map(function (e) { return "<li>" + esc(e) + "</li>"; }).join("");
    validationHtml = '<div class="validation-errors"><strong>Validation errors</strong><ul>' + errorItems + "</ul></div>";
  }

  var saveBtnText = editor.saving ? "Creating..." : "Create";

  detail.innerHTML =
    '<div class="editor-container' + savingClass + '">' +
      '<div class="editor-header">' +
        '<div class="editor-title">Create Work Item</div>' +
        '<div class="editor-actions">' +
          '<button class="cancel-btn" type="button">Cancel</button>' +
          '<button class="save-btn" type="button">' + saveBtnText + "</button>" +
        "</div>" +
      "</div>" +
      validationHtml +
      '<div class="editor-section">Fields</div>' +
      '<div class="editor-fields">' + fieldRows + "</div>" +
      '<div class="editor-section">Blocked by</div>' +
      '<div class="field-group">' +
        '<label>Add blocker (slug or external ref, press Enter)</label>' +
        '<input type="text" class="field-input" id="blockerInput" placeholder="e.g. other-item or EXT-123">' +
        '<div class="blocker-tags">' + tagHtml + '</div>' +
      '</div>' +
      '<div class="editor-section">Body</div>' +
      '<div class="md-editor">' +
        '<textarea class="md-input" id="mdInput" placeholder="Write Markdown..."></textarea>' +
        '<div class="md-preview" id="mdPreview"></div>' +
      "</div>" +
    "</div>";

  var mdInput = detail.querySelector("#mdInput");
  var mdPreview = detail.querySelector("#mdPreview");
  mdInput.value = d.body || "";
  updatePreview(d.body || "", mdPreview);

  detail.querySelector(".save-btn").addEventListener("click", saveWorkCreate);
  detail.querySelector(".cancel-btn").addEventListener("click", cancelEdit);

  // Wire field inputs
  detail.querySelectorAll(".field-input, .field-select").forEach(function (el) {
    if (el.id === "blockerInput") return;
    el.addEventListener("input", function () {
      var key = el.dataset.createField;
      if (el.type === "number") {
        editor.createDraft[key] = el.value === "" ? "" : el.value;
      } else {
        editor.createDraft[key] = el.value;
      }
      setDirty(true);
    });
  });

  // Wire blocker input
  var blockerInput = detail.querySelector("#blockerInput");
  if (blockerInput) {
    blockerInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        var val = blockerInput.value.trim();
        if (val) {
          if (!editor.createDraft.blockers) editor.createDraft.blockers = [];
          editor.createDraft.blockers.push(val);
          blockerInput.value = "";
          setDirty(true);
          render();
        }
      }
    });
  }

  detail.querySelectorAll(".remove-blocker").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var idx = parseInt(btn.dataset.index, 10);
      editor.createDraft.blockers.splice(idx, 1);
      setDirty(true);
      render();
    });
  });

  mdInput.addEventListener("input", function () {
    editor.createDraft.body = mdInput.value;
    updatePreview(mdInput.value, mdPreview);
    setDirty(true);
  });
}

function renderTaxonomyCreate() {
  var d = editor.createDraft;
  var savingClass = editor.saving ? " saving" : "";

  var fieldRows = TAXONOMY_FIELD_DESCRIPTORS.map(function (desc) {
    var value = d[desc.key];
    var inputHtml;
    if (desc.type === "select") {
      var options = (desc.options || []).map(function (opt) {
        var selected = (value === opt) ? " selected" : "";
        return '<option value="' + esc(opt) + '"' + selected + ">" + esc(opt) + "</option>";
      }).join("");
      inputHtml = '<select class="field-select" data-create-field="' + esc(desc.key) + '">' + options + "</select>";
    } else {
      inputHtml = '<input type="text" class="field-input" data-create-field="' + esc(desc.key) + '" value="' + esc(value || "") + '">';
    }
    return '<div class="field-group"><label>' + esc(desc.label) + (desc.key === "name" ? " *" : "") + "</label>" + inputHtml + "</div>";
  }).join("");

  // Vocabulary tag display
  var vocabTags = (d.vocabulary || []).map(function (v, i) {
    return '<span class="blocker-tag">' + esc(v) +
      '<button type="button" class="remove-tag" data-index="' + i + '">&times;</button></span>';
  }).join("");

  var validationHtml = "";
  if (editor.errors.length > 0) {
    var errorItems = editor.errors.map(function (e) { return "<li>" + esc(e) + "</li>"; }).join("");
    validationHtml = '<div class="validation-errors"><strong>Validation errors</strong><ul>' + errorItems + "</ul></div>";
  }

  var saveBtnText = editor.saving ? "Creating..." : "Create";

  detail.innerHTML =
    '<div class="editor-container' + savingClass + '">' +
      '<div class="editor-header">' +
        '<div class="editor-title">Create Taxonomy Term</div>' +
        '<div class="editor-actions">' +
          '<button class="cancel-btn" type="button">Cancel</button>' +
          '<button class="save-btn" type="button">' + saveBtnText + "</button>" +
        "</div>" +
      "</div>" +
      validationHtml +
      '<div class="editor-section">Fields</div>' +
      '<div class="editor-fields">' + fieldRows + "</div>" +
      '<div class="editor-section">Vocabulary refs (for Feature kind)</div>' +
      '<div class="field-group">' +
        '<label>Add vocabulary ref (press Enter)</label>' +
        '<input type="text" class="field-input" id="vocabInput" placeholder="vocabulary term slug">' +
        '<div class="blocker-tags">' + vocabTags + '</div>' +
      '</div>' +
      '<div class="editor-section">Description</div>' +
      '<div class="md-editor">' +
        '<textarea class="md-input" id="mdInput" placeholder="Write Markdown..."></textarea>' +
        '<div class="md-preview" id="mdPreview"></div>' +
      "</div>" +
    "</div>";

  var mdInput = detail.querySelector("#mdInput");
  var mdPreview = detail.querySelector("#mdPreview");
  mdInput.value = d.description || "";
  updatePreview(d.description || "", mdPreview);

  detail.querySelector(".save-btn").addEventListener("click", saveTaxonomyCreate);
  detail.querySelector(".cancel-btn").addEventListener("click", cancelEdit);

  detail.querySelectorAll(".field-input, .field-select").forEach(function (el) {
    if (el.id === "vocabInput") return;
    el.addEventListener("input", function () {
      var key = el.dataset.createField;
      editor.createDraft[key] = el.value;
      setDirty(true);
    });
  });

  var vocabInput = detail.querySelector("#vocabInput");
  if (vocabInput) {
    vocabInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        var val = vocabInput.value.trim();
        if (val) {
          if (!editor.createDraft.vocabulary) editor.createDraft.vocabulary = [];
          editor.createDraft.vocabulary.push(val);
          vocabInput.value = "";
          setDirty(true);
          render();
        }
      }
    });
  }

  detail.querySelectorAll(".remove-tag").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var idx = parseInt(btn.dataset.index, 10);
      editor.createDraft.vocabulary.splice(idx, 1);
      setDirty(true);
      render();
    });
  });

  mdInput.addEventListener("input", function () {
    editor.createDraft.description = mdInput.value;
    updatePreview(mdInput.value, mdPreview);
    setDirty(true);
  });
}

function renderCapabilityCreate() {
  var d = editor.createDraft;
  var savingClass = editor.saving ? " saving" : "";

  // Collection + name as text, status as select
  var collectionInput = '<div class="field-group"><label>Collection *</label>' +
    '<input type="text" class="field-input" data-create-field="collection" value="' + esc(d.collection || "") +
    '" placeholder="e.g. auth, web, routes"></div>';

  var nameInput = '<div class="field-group"><label>Name *</label>' +
    '<input type="text" class="field-input" data-create-field="name" value="' + esc(d.name || "") + '"></div>';

  var statusSelect = '<div class="field-group"><label>Status</label>' +
    '<select class="field-select" data-create-field="status">' +
    ['Supported', 'Partial', 'Missing', 'Blocked', 'Omitted'].map(function (opt) {
      var selected = (d.status === opt) ? " selected" : "";
      return '<option value="' + esc(opt) + '"' + selected + '">' + esc(opt) + '</option>';
    }).join("") + '</select></div>';

  var fieldRows = collectionInput + nameInput + statusSelect;

  var validationHtml = "";
  if (editor.errors.length > 0) {
    var errorItems = editor.errors.map(function (e) { return "<li>" + esc(e) + "</li>"; }).join("");
    validationHtml = '<div class="validation-errors"><strong>Validation errors</strong><ul>' + errorItems + "</ul></div>";
  }

  var saveBtnText = editor.saving ? "Creating..." : "Create";

  detail.innerHTML =
    '<div class="editor-container' + savingClass + '">' +
      '<div class="editor-header">' +
        '<div class="editor-title">Create Capability</div>' +
        '<div class="editor-actions">' +
          '<button class="cancel-btn" type="button">Cancel</button>' +
          '<button class="save-btn" type="button">' + saveBtnText + "</button>" +
        "</div>" +
      "</div>" +
      validationHtml +
      '<div class="editor-section">Fields</div>' +
      '<div class="editor-fields">' + fieldRows + "</div>" +
      '<p style="font-size:12px;color:var(--muted)">The collection is the namespace (capability file). ' +
        'Enter an existing collection name to add to it, or a new name to create a new collection.</p>' +
      '<div class="editor-section">Body</div>' +
      '<div class="md-editor">' +
        '<textarea class="md-input" id="mdInput" placeholder="Write Markdown..."></textarea>' +
        '<div class="md-preview" id="mdPreview"></div>' +
      "</div>" +
    "</div>";

  var mdInput = detail.querySelector("#mdInput");
  var mdPreview = detail.querySelector("#mdPreview");
  mdInput.value = d.body || "";
  updatePreview(d.body || "", mdPreview);

  detail.querySelector(".save-btn").addEventListener("click", saveCapabilityCreate);
  detail.querySelector(".cancel-btn").addEventListener("click", cancelEdit);

  detail.querySelectorAll(".field-input, .field-select").forEach(function (el) {
    el.addEventListener("input", function () {
      var key = el.dataset.createField;
      editor.createDraft[key] = el.value;
      setDirty(true);
    });
  });

  mdInput.addEventListener("input", function () {
    editor.createDraft.body = mdInput.value;
    updatePreview(mdInput.value, mdPreview);
    setDirty(true);
  });
}

// ============================================================
// ARTIFACT OPEN (existing behavior, preserved)
// ============================================================

async function openArtifact(slug, name) {
  try {
    var res = await fetch(
      "/api/work/" + encodeURIComponent(slug) + "/artifacts/" + encodeURIComponent(name) + "/open",
      { method: "POST", headers: { "Content-Type": "application/json" } }
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
// COMPLETE MODAL (restructured with inline submit handling)
// ============================================================

/**
 * Show the complete modal with DoD checklist, reconciliation reminder, and resolution.
 * Uses a self-contained approach: creates the DOM, wires buttons, removes on resolve.
 */
async function showCompleteModal(slug, item) {
  var payload = state.cachedWorkDetail;
  var dodItems = [];
  if (payload && payload.dodChecklist) {
    dodItems = payload.dodChecklist;
  }
  if (!dodItems.length) {
    dodItems = ["tests pass", "docs synced", "capabilities reconciled", "reviewed", "version offered"];
  }

  var checklistHtml = dodItems.map(function (dod, i) {
    return '<div class="dod-item">' +
      '<input type="checkbox" id="dod_' + i + '" class="dod-checkbox">' +
      '<label for="dod_' + i + '">' + esc(dod) + '</label></div>';
  }).join("");

  return new Promise(function (resolve) {
    var overlay = document.createElement("div");
    overlay.className = "modal-overlay";
    overlay.innerHTML =
      '<div class="modal-box" style="position:relative">' +
        '<button class="modal-dismiss" type="button" aria-label="Close">&times;</button>' +
        '<h2>Complete Work Item</h2>' +
        '<p>Complete "' + esc(item.title || slug) + '"?</p>' +
        '<div class="reconciliation-reminder">' +
          "<strong>Reconciliation reminder</strong><br>" +
          "Before completing: reconcile the capabilities ledger &mdash; flip the status of any " +
          "capabilities this work changed (Missing/Partial &rarr; Supported, etc.). " +
          "Web-complete does not do this for you." +
        '</div>' +
        '<div class="field-group">' +
          '<label>Resolution</label>' +
          '<select class="field-select" id="completeResolution">' +
            '<option value="">(select resolution)</option>' +
            '<option value="done">done</option>' +
            '<option value="wontfix">wontfix</option>' +
            '<option value="duplicate">duplicate</option>' +
            '<option value="superseded">superseded</option>' +
          '</select>' +
        '</div>' +
        '<h3>Definition of Done</h3>' +
        '<p style="font-size:12px;color:var(--muted)">All items must be acknowledged before completing.</p>' +
        '<div class="dod-list">' + checklistHtml + '</div>' +
        '<div id="completeError"></div>' +
        '<div class="modal-actions">' +
          '<button class="cancel-btn" type="button" id="completeCancel">Cancel</button>' +
          '<button class="save-btn" type="button" id="completeSubmitBtn" disabled>Complete</button>' +
          '<button class="action-btn" type="button" id="completeForceBtn" style="display:none;border-color:var(--warn);color:var(--warn)">Complete (ignore blockers)</button>' +
        '</div>' +
      '</div>';

    document.body.appendChild(overlay);

    function dismiss() {
      overlay.remove();
      resolve();
    }

    // Dismiss button
    overlay.querySelector(".modal-dismiss").addEventListener("click", dismiss);
    overlay.querySelector("#completeCancel").addEventListener("click", dismiss);

    // Close on overlay click
    overlay.addEventListener("click", function (e) {
      if (e.target === overlay) dismiss();
    });

    // Enable/disable submit based on DoD checkboxes + resolution
    function updateSubmitState() {
      var allChecked = Array.from(overlay.querySelectorAll(".dod-checkbox")).every(function (cb) {
        return cb.checked;
      });
      var resolution = overlay.querySelector("#completeResolution").value;
      var enabled = allChecked && resolution;
      overlay.querySelector("#completeSubmitBtn").disabled = !enabled;
    }

    overlay.querySelectorAll(".dod-checkbox").forEach(function (cb) {
      cb.addEventListener("change", updateSubmitState);
    });
    overlay.querySelector("#completeResolution").addEventListener("change", updateSubmitState);

    // Submit handler
    async function doComplete(force) {
      var resolution = overlay.querySelector("#completeResolution").value;
      var dodAck = Array.from(overlay.querySelectorAll(".dod-checkbox")).map(function (cb) {
        return dodItems[Array.from(overlay.querySelectorAll(".dod-checkbox")).indexOf(cb)];
      });

      overlay.querySelector("#completeSubmitBtn").disabled = true;
      overlay.querySelector("#completeSubmitBtn").textContent = "Completing...";
      overlay.querySelector("#completeForceBtn").style.display = "none";

      var res = await apiPost("/api/work/" + encodeURIComponent(slug) + "/actions/complete", {
        resolution: resolution,
        dod_ack: dodAck,
        force: force,
      });

      if (res.ok) {
        showToast("Work item completed");
        overlay.remove();
        await load();
        resolve();
      } else {
        // Show error inline in the modal
        var errorMsg = res.error || ("Complete failed (" + res.status + ")");
        var errorDiv = overlay.querySelector("#completeError");
        errorDiv.innerHTML = '<div class="modal-error">' + esc(errorMsg) + '</div>';

        // Show force button if this is a blocker error
        if (errorMsg.toLowerCase().indexOf("block") !== -1) {
          overlay.querySelector("#completeForceBtn").style.display = "";
        }

        overlay.querySelector("#completeSubmitBtn").disabled = false;
        overlay.querySelector("#completeSubmitBtn").textContent = "Complete";
      }
    }

    overlay.querySelector("#completeSubmitBtn").addEventListener("click", function () {
      doComplete(false);
    });

    overlay.querySelector("#completeForceBtn").addEventListener("click", function () {
      doComplete(true);
    });
  });
}

// ============================================================
// START ACTION - with inline error + force
// ============================================================

async function handleStartAction(slug) {
  var res = await apiPost("/api/work/" + encodeURIComponent(slug) + "/actions/start", {});

  if (res.ok) {
    showToast("Work item started");
    await load();
    return;
  }

  var errorMsg = res.error || ("Start failed (" + res.status + ")");
  var isBlocker = errorMsg.toLowerCase().indexOf("block") !== -1;

  if (res.status === 422 && isBlocker) {
    // Show force modal
    await new Promise(function (resolve) {
      var overlay = document.createElement("div");
      overlay.className = "modal-overlay";
      overlay.innerHTML =
        '<div class="modal-box" style="position:relative">' +
          '<button class="modal-dismiss" type="button" aria-label="Close">&times;</button>' +
          '<h2>Start Work Item</h2>' +
          '<p class="modal-error">' + esc(errorMsg) + '</p>' +
          '<p>This item has unresolved blockers. You can force-start it anyway.</p>' +
          '<div class="modal-actions">' +
            '<button class="cancel-btn" type="button" id="startCancel">Cancel</button>' +
            '<button class="save-btn" type="button" id="startForceBtn">Start (force)</button>' +
          '</div>' +
        '</div>';
      document.body.appendChild(overlay);

      function dismiss() { overlay.remove(); resolve(); }
      overlay.querySelector(".modal-dismiss").addEventListener("click", dismiss);
      overlay.querySelector("#startCancel").addEventListener("click", dismiss);
      overlay.addEventListener("click", function (e) { if (e.target === overlay) dismiss(); });

      overlay.querySelector("#startForceBtn").addEventListener("click", async function () {
        overlay.querySelector("#startForceBtn").disabled = true;
        overlay.querySelector("#startForceBtn").textContent = "Starting...";
        var r = await apiPost("/api/work/" + encodeURIComponent(slug) + "/actions/start", { force: true });
        if (r.ok) {
          showToast("Work item started (force)");
          overlay.remove();
          await load();
        } else {
          showToast(r.error || "Start failed");
          overlay.remove();
        }
        resolve();
      });
    });
  } else {
    showToast(errorMsg);
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
