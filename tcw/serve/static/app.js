const state = {
  view: "work",
  data: { work: [], taxonomy: [], capabilities: [] },
  selected: null,
  filter: "",
};

const labels = {
  work: "Work",
  taxonomy: "Taxonomy",
  capabilities: "Capabilities",
};

const list = document.querySelector("#list");
const detail = document.querySelector("#detail");
const summary = document.querySelector("#summary");
const filter = document.querySelector("#filter");
const listTitle = document.querySelector("#list-title");
const toast = document.querySelector("#toast");

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

async function fetchJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function load() {
  try {
    const [work, taxonomy, capabilities] = await Promise.all([
      fetchJson("/api/work"),
      fetchJson("/api/taxonomy"),
      fetchJson("/api/capabilities"),
    ]);
    state.data = { work, taxonomy, capabilities };
    state.selected = null;
    render();
  } catch (err) {
    detail.innerHTML = `<p class="empty">Failed to load: ${esc(err.message)}</p><button class="retry" type="button">Retry</button>`;
    detail.querySelector(".retry").addEventListener("click", load);
  }
}

function currentItems() {
  const items = state.data[state.view] || [];
  if (!state.filter) return items;
  const q = state.filter.toLowerCase();
  return items.filter((item) => JSON.stringify(item).toLowerCase().includes(q));
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
    return meta([item.status, item.effort && `effort ${item.effort}`, item.complexity && `complexity ${item.complexity}`]);
  }
  if (state.view === "taxonomy") {
    return meta([item.kind, item.origin, item.slug]);
  }
  return meta([item.status, item.file_id]);
}

function render() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.classList.toggle("active", tab.dataset.view === state.view);
  });
  listTitle.textContent = labels[state.view];
  const counts = `${state.data.work.length} work · ${state.data.taxonomy.length} taxonomy · ${state.data.capabilities.length} capabilities`;
  summary.textContent = counts;
  renderList();
  renderDetail();
}

function renderList() {
  const items = currentItems();
  if (!items.length) {
    list.innerHTML = `<p class="empty">No ${esc(labels[state.view].toLowerCase())} entries.</p>`;
    return;
  }
  list.innerHTML = items.map((item) => {
    const key = itemKey(item);
    const active = state.selected === key ? " active" : "";
    return `<button class="item${active}" type="button" data-key="${esc(key)}">
      <div class="item-title">${esc(itemTitle(item))}</div>
      <div class="item-meta">${itemMeta(item)}</div>
    </button>`;
  }).join("");
  list.querySelectorAll(".item").forEach((button) => {
    button.addEventListener("click", () => {
      state.selected = button.dataset.key;
      render();
    });
  });
}

function selectedItem() {
  const items = currentItems();
  if (!items.length) return null;
  return items.find((item) => itemKey(item) === state.selected) || items[0];
}

function renderDetail() {
  const item = selectedItem();
  if (!item) {
    detail.innerHTML = `<p class="empty">Select an entry.</p>`;
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

async function renderWork(item) {
  detail.innerHTML = `<p class="empty">Loading ${esc(item.slug)}...</p>`;
  try {
    const payload = await fetchJson(`/api/work/${encodeURIComponent(item.slug)}`);
    const got = payload.item;
    const artifacts = payload.artifacts.filter((artifact) => artifact.present && artifact.name !== "initial-request");
    detail.innerHTML = `
      <div class="detail-head">
        <div>
          <h2>${esc(got.title || got.slug)}</h2>
          <p class="item-meta">${esc(got.slug)}</p>
        </div>
        <span class="badge">${esc(got.status)}</span>
      </div>
      <div class="fields">
        ${field("Priority", got.priority ?? "-")}
        ${field("Effort", got.effort || "-")}
        ${field("Complexity", got.complexity || "-")}
        ${field("Resolution", got.resolution || "-")}
      </div>
      <div class="artifacts">
        ${artifacts.map((artifact) => `<button class="artifact" type="button" data-name="${esc(artifact.name)}">${esc(artifact.name)}</button>`).join("")}
      </div>
      <article class="body">${marked.parse(got.body || "")}</article>`;
    detail.querySelectorAll(".artifact").forEach((button) => {
      button.addEventListener("click", () => openArtifact(got.slug, button.dataset.name));
    });
  } catch (err) {
    detail.innerHTML = `<p class="empty">Failed to load work item: ${esc(err.message)}</p>`;
  }
}

function field(name, value) {
  return `<div class="field"><span>${esc(name)}</span>${esc(value)}</div>`;
}

function renderTaxonomy(item) {
  detail.innerHTML = `
    <div class="detail-head">
      <div>
        <h2>${esc(item.name)}</h2>
        <p class="item-meta">${esc(item.qualified || item.slug)}</p>
      </div>
      <span class="badge">${esc(item.kind)}</span>
    </div>
    <div class="fields">
      ${field("Origin", item.origin)}
      ${field("Relates to", (item.relates_to || []).join(", ") || "-")}
      ${field("Vocabulary", (item.vocabulary || []).join(", ") || "-")}
      ${field("Attachments", (item.attachments || []).join(", ") || "-")}
    </div>
    <article class="body">${marked.parse(item.description || "")}</article>`;
}

function renderCapability(item) {
  const fields = item.fields || {};
  detail.innerHTML = `
    <div class="detail-head">
      <div>
        <h2>${esc(item.name)}</h2>
        <p class="item-meta">${esc(item.ref)}</p>
      </div>
      <span class="badge">${esc(fields.Status || "Unspecified")}</span>
    </div>
    <div class="fields">
      ${Object.entries(fields).map(([key, value]) => field(key, value)).join("")}
    </div>
    <article class="body">${marked.parse(item.body || "")}</article>`;
}

async function openArtifact(slug, name) {
  try {
    const res = await fetch(`/api/work/${encodeURIComponent(slug)}/artifacts/${encodeURIComponent(name)}/open`, { method: "POST" });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    if (res.status === 204) {
      showToast("Opened artifact");
      return;
    }
    const payload = await res.json();
    if (payload.url) window.open(payload.url, "_blank", "noopener");
  } catch (err) {
    showToast(`Could not open artifact: ${err.message}`);
  }
}

function showToast(message) {
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => { toast.hidden = true; }, 2800);
}

document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    state.view = tab.dataset.view;
    state.selected = null;
    render();
  });
});

filter.addEventListener("input", () => {
  state.filter = filter.value;
  state.selected = null;
  render();
});

load();
