import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import { marked } from "marked";
import { useBeforeUnload, useLocation, useNavigate } from "react-router";
import { encodeRef, fetchJson, requestJson } from "../model/api";
import { buildPathTree, buildWorkTree, pathAncestors, pruneTree, workAncestors } from "../model/tree";
import { referenceOptions, type TReferenceField } from "../model/reference-search";
import { ReferenceInput } from "./reference-input";
import type {
  Axis,
  AxisItem,
  CapabilityDetail,
  CapabilityItem,
  JsonRecord,
  ResourceDetail,
  TaxonomyDetail,
  TaxonomyItem,
  TMutationResponse,
  TreeNode,
  WorkDetail,
  WorkItem,
} from "../model/types";

const AXES: Axis[] = ["taxonomy", "capabilities", "work"];
const LABELS: Record<Axis, string> = { work: "Work", taxonomy: "Taxonomy", capabilities: "Capabilities" };
const WORK_STATUSES = ["backlog", "active", "completed"];
const CAPABILITY_FIELDS = [
  ["Status", ["", "Supported", "Partial", "Missing", "Blocked", "Omitted"]],
  ["Priority", ["", "P0", "P1", "P2", "P3"]],
  ["Lifecycle", ["", "Experimental", "Stable", "Deprecated"]],
  ["Feature", null], ["Subject", null], ["Roles", null], ["When", null],
  ["Gaps", null], ["Blocked by", null], ["Tracker", null], ["Planning doc", null],
  ["Superseded by", null],
] as const;

type Data = { work: WorkItem[]; taxonomy: TaxonomyItem[]; capabilities: CapabilityItem[] };
type Detail = WorkDetail | TaxonomyDetail | CapabilityDetail;
type Draft = Record<string, unknown> & { body?: string };
type Editor =
  | { mode: "create"; axis: Axis; draft: Draft }
  | { mode: "core"; axis: Axis; ref: string; revision: string; draft: Draft; original: Draft }
  | { mode: "resource"; axis: "work"; kind: "artifacts" | "sidecars" | "plan-stages"; slug: string; name: string;
      revision: string; mediaType: string; draft: string; original: string };

function itemKey(axis: Axis, item: AxisItem): string {
  if (axis === "work") return (item as WorkItem).slug;
  if (axis === "taxonomy") {
    const term = item as TaxonomyItem;
    return term.qualified ?? term.slug;
  }
  const capability = item as CapabilityItem;
  return capability.qualified ?? capability.path;
}

function itemTitle(axis: Axis, item: AxisItem): string {
  if (axis === "work") return (item as WorkItem).title ?? (item as WorkItem).slug;
  if (axis === "taxonomy") return (item as TaxonomyItem).name ?? (item as TaxonomyItem).slug;
  return (item as CapabilityItem).name ?? (item as CapabilityItem).path;
}

function pathFor(axis: Axis, key: string | null): string {
  if (!key) return `/${axis}`;
  if (axis === "work") {
    const parts = key.split("/");
    const slug = parts.pop()!;
    return `/${[...parts, "work", slug].map(encodeURIComponent).join("/")}`;
  }
  return `/${[axis, ...key.split("/")].map(encodeURIComponent).join("/")}`;
}

function parsePath(pathname: string): { axis: Axis; key: string | null } {
  const segments = pathname.split("/").filter(Boolean).map(decodeURIComponent);
  const axisIndex = segments.findIndex((segment) => AXES.includes(segment as Axis));
  if (axisIndex === -1) return { axis: "work", key: null };
  const axis = segments[axisIndex] as Axis;
  const rest = [...segments.slice(0, axisIndex), ...segments.slice(axisIndex + 1)];
  return { axis, key: rest.length ? rest.join("/") : null };
}

function Markdown({ source, resolveLinks = false }: { source: string; resolveLinks?: boolean }) {
  const container = useRef<HTMLElement>(null);
  const html = useMemo(() => marked.parse(source || "") as string, [source]);
  useEffect(() => {
    if (!resolveLinks || !container.current) return;
    const anchors = [...container.current.querySelectorAll<HTMLAnchorElement>('a[href^="tcw://"]')];
    if (!anchors.length) return;
    const uris = anchors.map((anchor) => anchor.getAttribute("href")!);
    void requestJson<Record<string, { ok: boolean; axis?: Axis; key?: string }>>("/api/resolve", "POST", { uris })
      .then((result) => {
        for (const anchor of anchors) {
          const uri = anchor.getAttribute("href")!;
          const resolved = result.data?.[uri];
          if (resolved?.ok && resolved.axis && resolved.key) {
            anchor.href = pathFor(resolved.axis, resolved.key);
            anchor.dataset.navAxis = resolved.axis;
            anchor.dataset.navKey = resolved.key;
          } else {
            anchor.classList.add("tcw-inert");
            anchor.title = uri;
          }
        }
      });
  }, [html, resolveLinks]);
  return <article ref={container} className="body" dangerouslySetInnerHTML={{ __html: html }} />;
}

function Fields({ children }: { children: ReactNode }) { return <div className="fields">{children}</div>; }
function Field({ name, value }: { name: string; value: unknown }) {
  return <div className="field"><span>{name}</span>{String(value ?? "-")}</div>;
}
function Errors({ errors }: { errors: string[] }) {
  return errors.length ? <div className="validation-errors"><strong>Validation errors</strong>
    <ul>{errors.map((error) => <li key={error}>{error}</li>)}</ul></div> : null;
}

function Modal({ title, children, onClose }: { title: string; children: ReactNode; onClose: () => void }) {
  return <div className="modal-overlay" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="modal-box">
      <button className="modal-dismiss" type="button" aria-label="Close" onClick={onClose}>×</button>
      <h2>{title}</h2>{children}
    </div>
  </div>;
}

function Tree<T extends AxisItem>({ nodes, axis, selected, expanded, onToggle, onSelect, visible }:
  { nodes: Array<TreeNode<T>>; axis: Axis; selected: string | null; expanded: Set<string>;
    onToggle: (path: string) => void; onSelect: (key: string) => void; visible: (item: T) => boolean }) {
  const renderNodes = (current: Array<TreeNode<T>>, depth: number): ReactNode => current.map((node) => {
    const hasChildren = node.children.length > 0;
    const isExpanded = expanded.has(node.path);
    const key = node.item ? itemKey(axis, node.item) : node.path;
    return <div className="tree-node" key={node.path} role="none">
      <div className="tree-row" role="none">
        {Array.from({ length: depth }, (_, index) => <span className="tree-indent" key={index} />)}
        {hasChildren
          ? <button className="tree-toggle" type="button" tabIndex={-1} aria-hidden="true"
              onClick={() => onToggle(node.path)}>{isExpanded ? "▾" : "▸"}</button>
          : <span className="tree-spacer" />}
        {node.item
          ? <div className={axis === "work" ? "item-row" : "tree-item-content"}>
              <button type="button" role="treeitem" aria-level={depth + 1} data-tree-path={node.path}
                aria-expanded={hasChildren ? isExpanded : undefined} aria-selected={selected === key}
                className={`item${selected === key ? " active" : ""}${visible(node.item) ? "" : " ancestor-dim"}`}
                onClick={() => onSelect(key)}>
                <div className="item-title">{itemTitle(axis, node.item)}</div>
                <div className="item-meta"><ItemMeta axis={axis} item={node.item} /></div>
              </button>
              {axis === "work" && <button className="copy-slug" type="button" title="Copy slug"
                aria-label="Copy slug to clipboard" onClick={() => void navigator.clipboard.writeText(key)}>⎘</button>}
            </div>
          : <button className="tree-folder" type="button" role="treeitem" aria-level={depth + 1} data-tree-path={node.path}
              aria-expanded={isExpanded} onClick={() => onToggle(node.path)}>{node.name}</button>}
      </div>
      {hasChildren && isExpanded ? renderNodes(node.children, depth + 1) : null}
    </div>;
  });
  return <>{renderNodes(nodes, 0)}</>;
}

function ItemMeta({ axis, item }: { axis: Axis; item: AxisItem }) {
  if (axis === "work") {
    const work = item as WorkItem;
    return <><span className={`status-badge st-${work.status}`}>{work.status}</span>{" "}
      {[work.effort && `effort ${work.effort}`, work.complexity && `complexity ${work.complexity}`,
        work.tags?.length && `tags ${work.tags.join(", ")}`].filter(Boolean).join(" · ")}</>;
  }
  if (axis === "taxonomy") {
    const term = item as TaxonomyItem;
    return <>{[term.kind, term.origin].filter(Boolean).join(" · ")}</>;
  }
  const capability = item as CapabilityItem;
  return <>{[capability.status, capability.origin !== "local" && capability.origin].filter(Boolean).join(" · ")}</>;
}

function MarkdownEditor({ value, onChange, placeholder = "Write Markdown..." }:
  { value: string; onChange: (value: string) => void; placeholder?: string }) {
  const [fraction, setFraction] = useState(0.5);
  return <div className="md-editor" style={{ "--md-split": `${fraction * 100}%` } as CSSProperties}>
    <textarea className="md-input" aria-label="Markdown" value={value} placeholder={placeholder}
      onChange={(event) => onChange(event.target.value)} />
    <div className="md-resizer" role="separator" aria-orientation="vertical" aria-label="Resize Markdown editor"
      onPointerDown={(event) => beginResize(event, event.currentTarget.parentElement!, 0.2, 0.8, setFraction)} />
    <div className="md-preview"><Markdown source={value} /></div>
  </div>;
}

function beginResize(
  event: ReactPointerEvent<HTMLElement>,
  container: HTMLElement,
  minimum: number,
  maximum: number,
  onChange: (fraction: number) => void,
) {
  event.preventDefault();
  const move = (pointer: PointerEvent) => {
    const bounds = container.getBoundingClientRect();
    onChange(Math.min(maximum, Math.max(minimum, (pointer.clientX - bounds.left) / bounds.width)));
  };
  const stop = () => {
    window.removeEventListener("pointermove", move);
    window.removeEventListener("pointerup", stop);
  };
  window.addEventListener("pointermove", move);
  window.addEventListener("pointerup", stop);
}

function loadExpanded(): Record<Axis, Set<string>> {
  const empty = (): Record<Axis, Set<string>> => ({ work: new Set(), taxonomy: new Set(), capabilities: new Set() });
  try {
    const stored = JSON.parse(localStorage.getItem("tcw.treeExpanded") ?? "{}") as Partial<Record<Axis, string[]>>;
    return { work: new Set(stored.work), taxonomy: new Set(stored.taxonomy), capabilities: new Set(stored.capabilities) };
  } catch { return empty(); }
}

function TextInput({ label, value, onChange, type = "text", placeholder }:
  { label: string; value: string | number; onChange: (value: string) => void; type?: string; placeholder?: string }) {
  return <div className="field-group"><label>{label}</label>
    <input className="field-input" aria-label={label} type={type} value={value} placeholder={placeholder}
      onChange={(event) => onChange(event.target.value)} /></div>;
}

function SelectInput({ label, value, options, onChange }:
  { label: string; value: string; options: readonly string[]; onChange: (value: string) => void }) {
  return <div className="field-group"><label>{label}</label><select className="field-select" aria-label={label}
    value={value} onChange={(event) => onChange(event.target.value)}>
    {options.map((option) => <option value={option} key={option}>{option || "(unset)"}</option>)}
  </select></div>;
}

export function App() {
  const location = useLocation();
  const navigate = useNavigate();
  const initialRoute = useRef(parsePath(location.pathname)).current;
  const [axis, setAxis] = useState<Axis>(initialRoute.axis);
  const [selected, setSelected] = useState<string | null>(initialRoute.key);
  const [data, setData] = useState<Data>({ work: [], taxonomy: [], capabilities: [] });
  const [registeredTags, setRegisteredTags] = useState<string[]>([]);
  const [filter, setFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<Record<string, boolean>>({ backlog: true, active: true, completed: false });
  const [kindFilter, setKindFilter] = useState<string[]>([]);
  const [tagFilter, setTagFilter] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<Record<Axis, Set<string>>>(loadExpanded);
  const [seenPaths, setSeenPaths] = useState<Record<Axis, Set<string>>>(() => ({ work: new Set(), taxonomy: new Set(), capabilities: new Set() }));
  const [listWidth, setListWidth] = useState(() => {
    const stored = Number.parseFloat(localStorage.getItem("tcw.listWidth") ?? "");
    return Number.isFinite(stored) && stored >= 0.12 && stored <= 0.6 ? stored : 0.28;
  });
  const [detail, setDetail] = useState<Detail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [editor, setEditor] = useState<Editor | null>(null);
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [conflict, setConflict] = useState<unknown>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [toast, setToast] = useState("");
  const [modal, setModal] = useState<"drop" | "start" | "complete" | null>(null);
  const [loadError, setLoadError] = useState("");

  const showToast = useCallback((message: string) => {
    setToast(message); window.setTimeout(() => setToast(""), 2800);
  }, []);
  const showSaveResult = useCallback((message: string, response: JsonRecord | null) => {
    const findings = asWarnings(response);
    setWarnings(findings);
    showToast(findings.length ? `${message} with ${findings.length} validation issue${findings.length === 1 ? "" : "s"}` : message);
  }, [showToast]);
  const confirmLeave = useCallback(() => !dirty || window.confirm("You have unsaved changes. Leave without saving?"), [dirty]);
  useBeforeUnload(useCallback((event) => { if (dirty) event.preventDefault(); }, [dirty]));

  const load = useCallback(async (preserveSelection = true) => {
    try {
      const [work, taxonomy, capabilities, tags] = await Promise.all([
        fetchJson<WorkItem[]>("/api/work"), fetchJson<TaxonomyItem[]>("/api/taxonomy"),
        fetchJson<CapabilityItem[]>("/api/capabilities"),
        fetchJson<{ tags: string[] }>("/api/work/tags").catch(() => ({ tags: [] })),
      ]);
      setData({ work, taxonomy, capabilities });
      setRegisteredTags(tags.tags ?? []);
      if (!preserveSelection) setSelected(null);
      setLoadError("");
    } catch (error) { setLoadError(error instanceof Error ? error.message : String(error)); }
  }, []);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    localStorage.setItem("tcw.treeExpanded", JSON.stringify(Object.fromEntries(
      AXES.map((candidate) => [candidate, [...expanded[candidate]]]),
    )));
  }, [expanded]);
  useEffect(() => { localStorage.setItem("tcw.listWidth", String(listWidth)); }, [listWidth]);
  useEffect(() => {
    const route = parsePath(location.pathname);
    if (route.axis !== axis || route.key !== selected) {
      if (!confirmLeave()) { navigate(pathFor(axis, selected), { replace: true }); return; }
      setEditor(null); setDirty(false); setDetail(null); setAxis(route.axis); setSelected(route.key);
    }
  }, [location.pathname]); // eslint-disable-line react-hooks/exhaustive-deps

  const currentItems = data[axis] as AxisItem[];
  useEffect(() => {
    if (!selected || !(data[axis] as AxisItem[]).some((item) => itemKey(axis, item) === selected)) {
      setDetail(null); return;
    }
    setLoadingDetail(true);
    const path = axis === "work" ? `/api/work/${encodeRef(selected)}` :
      axis === "taxonomy" ? `/api/taxonomy/${encodeRef(selected)}` : `/api/capabilities/${encodeRef(selected)}`;
    void fetchJson<Detail>(path).then(setDetail).catch((error) => setLoadError(String(error))).finally(() => setLoadingDetail(false));
  }, [axis, selected, data]);

  const navigateTo = (nextAxis: Axis, key: string | null) => {
    if (!confirmLeave()) return;
    setEditor(null); setDirty(false); setErrors([]); setConflict(null);
    setDetail(null); setAxis(nextAxis); setSelected(key); navigate(pathFor(nextAxis, key));
    if (key) {
      const ancestors = nextAxis === "work" ? workAncestors(key, data.work) : pathAncestors(key);
      setExpanded((old) => ({ ...old, [nextAxis]: new Set([...old[nextAxis], ...ancestors]) }));
    }
  };

  const visible = useCallback((item: AxisItem) => {
    if (axis === "work") {
      const work = item as WorkItem;
      if (work.status && statusFilter[work.status] === false) return false;
      if (tagFilter.length && !tagFilter.some((tag) => work.tags?.includes(tag))) return false;
    }
    if (axis === "taxonomy" && kindFilter.length && !kindFilter.includes((item as TaxonomyItem).kind ?? "")) return false;
    return !filter || JSON.stringify(item).toLowerCase().includes(filter.toLowerCase());
  }, [axis, filter, kindFilter, statusFilter, tagFilter]);

  const tree = useMemo(() => {
    const built = axis === "work" ? buildWorkTree(data.work) : buildPathTree(currentItems, (item) => itemKey(axis, item));
    const filtering = Boolean(filter || kindFilter.length || tagFilter.length ||
      (axis === "work" && WORK_STATUSES.some((status) => !statusFilter[status])));
    if (!filtering) return { nodes: built as Array<TreeNode<AxisItem>>, forced: new Set<string>() };
    const pruned = pruneTree(built as Array<TreeNode<AxisItem>>, visible);
    return { nodes: pruned.nodes, forced: filter ? pruned.forceExpand : new Set<string>() };
  }, [axis, currentItems, data.work, filter, kindFilter, statusFilter, tagFilter, visible]);
  const effectiveExpanded = useMemo(() => new Set([...expanded[axis], ...tree.forced]), [axis, expanded, tree.forced]);
  useEffect(() => {
    const parents: string[] = [];
    const collect = (nodes: Array<TreeNode<AxisItem>>) => nodes.forEach((node) => {
      if (node.children.length) { parents.push(node.path); collect(node.children); }
    });
    collect(tree.nodes);
    const unseen = parents.filter((path) => !seenPaths[axis].has(path));
    if (!unseen.length) return;
    setSeenPaths((old) => ({ ...old, [axis]: new Set([...old[axis], ...unseen]) }));
    setExpanded((old) => ({ ...old, [axis]: new Set([...old[axis], ...unseen]) }));
  }, [axis, seenPaths, tree.nodes]);

  const setDraft = (key: string, value: unknown) => {
    setEditor((current) => {
      if (!current) return current;
      if (current.mode === "resource") {
        return key === "draft" ? { ...current, draft: String(value) } : current;
      }
      return { ...current, draft: { ...current.draft, [key]: value } } as Editor;
    });
    setDirty(true);
  };

  const enterCreate = () => {
    const draft = axis === "work" ? { title: "", priority: "", effort: "", complexity: "", parent: "", initiative: "", blockers: [], tags: [], body: "" }
      : axis === "taxonomy" ? { name: "", kind: "Vocabulary", slug: "", parent: "", vocabulary: [], description: "", body: "" }
      : { path: "", name: "", status: "Missing", body: "" };
    setEditor({ mode: "create", axis, draft }); setSelected(null); setDirty(false); setErrors([]); setConflict(null);
  };

  const enterCore = () => {
    if (!detail) return;
    let draft: Draft; let ref: string; let revision: string;
    if (axis === "work") {
      const payload = detail as WorkDetail; const item = payload.item;
      draft = { title: item.title ?? "", priority: item.priority ?? "", effort: item.effort ?? "",
        complexity: item.complexity ?? "", parent: item.parent ?? "", initiative: item.initiative ?? "",
        blockers: (item.blocked_by ?? []).map((blocker) => blocker.slug ?? blocker.external ?? "").filter(Boolean),
        tags: item.tags ?? [], body: item.body ?? "" };
      ref = item.slug; revision = payload.coreRevision;
    } else if (axis === "taxonomy") {
      const payload = detail as TaxonomyDetail; const term = payload.term;
      draft = { name: term.name ?? "", kind: term.kind ?? "Vocabulary", relates_to: term.relates_to ?? [],
        vocabulary: term.vocabulary ?? [], body: term.description ?? "" };
      ref = term.qualified ?? term.slug; revision = payload.coreRevision;
    } else {
      const payload = detail as CapabilityDetail; const capability = payload.capability;
      draft = { ...(capability.fields ?? {}), body: capability.body ?? "" };
      ref = capability.path; revision = payload.coreRevision;
    }
    setEditor({ mode: "core", axis, ref, revision, draft, original: structuredClone(draft) });
    setDirty(false); setErrors([]); setConflict(null);
  };

  const enterResource = async (kind: "artifacts" | "sidecars" | "plan-stages", slug: string, name: string) => {
    try {
      const resource = await fetchJson<ResourceDetail>(`/api/work/${encodeRef(slug)}/${kind}/${encodeRef(name)}`);
      setEditor({ mode: "resource", axis: "work", kind, slug, name, revision: resource.revision,
        mediaType: resource.mediaType ?? (kind === "artifacts" ? "text/markdown" : "application/yaml"),
        draft: resource.content, original: resource.content });
      setDirty(false); setErrors([]); setConflict(null);
    } catch (error) {
      if (kind === "plan-stages") {
        const draft = "## Objective\n\n\n\n## Pre-stage checks\n\n\n\n## Implementation\n\n\n\n## Post-stage checks\n\n";
        setEditor({ mode: "resource", axis: "work", kind, slug, name, revision: "",
          mediaType: "text/markdown", draft, original: "" });
        setDirty(false); setErrors([]); setConflict(null); return;
      }
      showToast(`Failed to load ${kind === "artifacts" ? "artifact" : "sidecar"}: ${String(error)}`);
    }
  };

  const cancelEditor = () => {
    if (dirty && !window.confirm("You have unsaved changes. Discard them?")) return;
    setEditor(null); setDirty(false); setErrors([]); setConflict(null);
  };

  const save = async () => {
    if (!editor || saving) return;
    setSaving(true); setErrors([]); setConflict(null);
    try {
      if (editor.mode === "create") {
        const draft = editor.draft;
        let path: string; let body: JsonRecord;
        if (editor.axis === "work") {
          if (!String(draft.title ?? "").trim()) { setErrors(["Title is required"]); return; }
          path = "/api/work";
          body = compact({ title: String(draft.title).trim(), priority: draft.priority === "" ? undefined : Number(draft.priority),
            effort: draft.effort, complexity: draft.complexity, parent: draft.parent, initiative: draft.initiative,
            blockers: draft.blockers, tags: draft.tags, body: draft.body });
        } else if (editor.axis === "taxonomy") {
          if (!String(draft.name ?? "").trim()) { setErrors(["Name is required"]); return; }
          path = "/api/taxonomy";
          body = compact({ name: String(draft.name).trim(), kind: draft.kind, slug: draft.slug, parent: draft.parent,
            vocabulary: draft.vocabulary, description: draft.body });
        } else {
          if (!String(draft.path ?? "").trim()) { setErrors(["Path is required"]); return; }
          path = "/api/capabilities";
          body = compact({ path: String(draft.path).trim(), name: draft.name, status: draft.status, body: draft.body });
        }
        const result = await requestJson<JsonRecord>(path, "POST", body);
        if (!result.ok) { setErrors([result.error || `Create failed (${result.status})`]); return; }
        showSaveResult(`${LABELS[editor.axis]} created`, result.data);
      } else if (editor.mode === "core") {
        const fields: JsonRecord = {};
        for (const [key, value] of Object.entries(editor.draft)) {
          if (key !== "body" && JSON.stringify(value) !== JSON.stringify(editor.original[key])) fields[key] = value;
        }
        if (editor.axis === "work" && "priority" in fields) {
          fields.priority = fields.priority === "" ? null : Number(fields.priority);
        }
        if (editor.axis === "capabilities") {
          for (const key of ["Feature", "Blocked by", "Planning doc", "Superseded by"]) {
            if (fields[key] === "") fields[key] = null;
          }
        }
        const body: JsonRecord = { revision: editor.revision, fields };
        if (editor.draft.body !== editor.original.body) body.body = editor.draft.body;
        const path = editor.axis === "work" ? `/api/work/${encodeRef(editor.ref)}` :
          editor.axis === "taxonomy" ? `/api/taxonomy/${encodeRef(editor.ref)}` : `/api/capabilities/${encodeRef(editor.ref)}`;
        const result = await requestJson<JsonRecord>(path, "PATCH", body);
        if (result.status === 409) { setConflict({ local: structuredClone(editor.draft) }); return; }
        if (!result.ok) { setErrors([result.error || `Save failed (${result.status})`]); return; }
        showSaveResult("Saved", result.data);
      } else {
        const result = await requestJson<ResourceDetail & TMutationResponse>(
          `/api/work/${encodeRef(editor.slug)}/${editor.kind}/${encodeRef(editor.name)}`, "PUT",
          { name: editor.name, content: editor.draft, mediaType: editor.mediaType, revision: editor.revision });
        if (result.status === 409) { setConflict({ local: editor.draft }); return; }
        if (!result.ok) { setErrors([result.error || `Save failed (${result.status})`]); return; }
        showSaveResult(editor.kind === "artifacts" ? "Artifact saved" : "Sidecar saved", result.data);
      }
      setEditor(null); setDirty(false); await load();
    } catch (error) { setErrors([error instanceof Error ? error.message : String(error)]); }
    finally { setSaving(false); }
  };

  const refreshConflict = async () => {
    if (!editor) return;
    if (!window.confirm("Replace your draft with the current server version?")) return;
    setEditor(null); setDirty(false); setConflict(null); await load();
  };

  const doAction = async (action: "start" | "complete" | "drop", options: JsonRecord = {}) => {
    if (!selected) return false;
    const result = action === "drop"
      ? await requestJson<JsonRecord>(`/api/work/${encodeRef(selected)}`, "DELETE")
      : await requestJson<JsonRecord>(`/api/work/${encodeRef(selected)}/actions/${action}`, "POST", options);
    if (!result.ok) { setErrors([result.error || `${action} failed`]); return false; }
    setModal(null); showToast(`Work item ${action === "complete" ? "completed" : `${action}ed`}`);
    await load(action !== "drop"); if (action === "drop") navigateTo("work", null);
    return true;
  };

  const deletePlanStage = async (slug: string, name: string, revision?: string) => {
    if (!window.confirm(`Delete plan stage ${name}?`)) return;
    const response = await fetch(`/api/work/${encodeRef(slug)}/plan-stages/${encodeRef(name)}`, {
      method: "DELETE", headers: revision ? { "X-TCW-Revision": revision } : undefined,
    });
    if (response.status === 409) { showToast("Plan stage changed; refresh before deleting"); return; }
    if (!response.ok) { showToast(`Could not delete plan stage: ${response.statusText}`); return; }
    showToast("Plan stage deleted"); await load();
  };

  return <>
    <header className="topbar"><div><h1>TCW</h1><p>{data.taxonomy.length} taxonomy · {data.capabilities.length} capabilities · {data.work.length} work items</p></div>
      <nav className="tabs" aria-label="TCW views">{AXES.map((candidate) => <button type="button" key={candidate}
        className={`tab${axis === candidate ? " active" : ""}`} onClick={() => navigateTo(candidate, null)}>{LABELS[candidate]}</button>)}</nav>
    </header>
    <main className="shell" style={{ "--list-width": `${listWidth * 100}%` } as CSSProperties}>
      <section className="list-pane"><div className="list-head"><h2>{LABELS[axis]}</h2>
        <input type="search" placeholder="Filter" value={filter} onChange={(event) => {
          if (editor && !confirmLeave()) return; setEditor(null); setDirty(false); setFilter(event.target.value); navigateTo(axis, null);
        }} /></div>
        <FilterControls axis={axis} registeredTags={registeredTags} statusFilter={statusFilter}
          setStatusFilter={setStatusFilter} kindFilter={kindFilter} setKindFilter={setKindFilter}
          tagFilter={tagFilter} setTagFilter={setTagFilter} />
        <div className="create-row">
          <button className="create-btn" type="button" onClick={enterCreate}>+ Create {LABELS[axis]}</button>
        </div>
        <div className="list" role="tree" aria-label="Objects" onKeyDown={handleTreeKeyboard}>
          {tree.nodes.length ? <Tree nodes={tree.nodes} axis={axis} selected={selected} expanded={effectiveExpanded}
            visible={visible} onSelect={(key) => navigateTo(axis, key)} onToggle={(path) => {
              if (filter) return; setExpanded((old) => { const next = new Set(old[axis]);
                if (next.has(path)) next.delete(path); else next.add(path); return { ...old, [axis]: next }; });
            }} /> : <p className="empty">No {LABELS[axis].toLowerCase()} entries.</p>}
        </div>
      </section>
      <div className="col-resizer" role="separator" aria-orientation="vertical" aria-label="Resize list column"
        onPointerDown={(event) => beginResize(event, event.currentTarget.parentElement!, 0.12, 0.6, setListWidth)} />
      <section className="detail-pane" aria-live="polite" onClick={(event) => {
        const anchor = (event.target as HTMLElement).closest<HTMLAnchorElement>("a[data-nav-key]");
        if (anchor) { event.preventDefault(); navigateTo(anchor.dataset.navAxis as Axis, anchor.dataset.navKey!); }
      }}>
        {warnings.length > 0 && <div className="warnings-banner" role="alert"><strong>Saved with validation issues</strong><ul>{warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
        {loadError ? <><p className="empty">Failed to load: {loadError}</p><button type="button" onClick={() => void load()}>Retry</button></> :
          editor ? <EditorView editor={editor} setDraft={setDraft} saving={saving} errors={errors} conflict={conflict}
            registeredTags={registeredTags} data={data} onSave={() => void save()} onCancel={cancelEditor} onRefreshConflict={() => void refreshConflict()} /> :
          loadingDetail ? <p className="empty">Loading...</p> : detail ? <DetailView axis={axis} detail={detail}
            onEdit={enterCore} onResource={(kind, slug, name) => void enterResource(kind, slug, name)}
            onOpen={(slug, name, kind = "artifacts") => void openWorkResource(slug, name, kind, showToast)}
            onDeletePlanStage={(slug, name, revision) => void deletePlanStage(slug, name, revision)}
            onAction={(action) => setModal(action)} /> : <p className="empty">Select an entry.</p>}
      </section>
    </main>
    {toast && <div className="toast">{toast}</div>}
    {modal === "drop" && selected && <Modal title="Drop Work Item" onClose={() => setModal(null)}>
      <p>This permanently drops <strong>{selected}</strong>.</p><div className="modal-actions"><button type="button" onClick={() => setModal(null)}>Cancel</button>
        <button className="action-btn drop" type="button" onClick={() => void doAction("drop")}>Drop</button></div></Modal>}
    {modal === "start" && <StartModal onClose={() => setModal(null)} onStart={(force) => doAction("start", force ? { force: true } : {})} errors={errors} />}
    {modal === "complete" && detail && <CompleteModal detail={detail as WorkDetail} onClose={() => setModal(null)}
      onComplete={(options) => doAction("complete", options)} errors={errors} />}
  </>;
}

function compact(record: JsonRecord): JsonRecord {
  return Object.fromEntries(Object.entries(record).filter(([, value]) => value !== undefined && value !== "" &&
    (!Array.isArray(value) || value.length > 0)));
}

function handleTreeKeyboard(event: ReactKeyboardEvent<HTMLDivElement>) {
  const target = (event.target as HTMLElement).closest<HTMLElement>('[role="treeitem"]');
  if (!target) return;
  const keys = ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "End"];
  if (!keys.includes(event.key)) return;
  event.preventDefault();
  const items = [...event.currentTarget.querySelectorAll<HTMLElement>('[role="treeitem"]')];
  const index = items.indexOf(target);
  const focus = (next: number) => items[next]?.focus();
  if (event.key === "ArrowUp") focus(index - 1);
  else if (event.key === "ArrowDown") focus(index + 1);
  else if (event.key === "Home") focus(0);
  else if (event.key === "End") focus(items.length - 1);
  else if (event.key === "ArrowRight") {
    if (target.getAttribute("aria-expanded") === "false") {
      target.closest(".tree-row")?.querySelector<HTMLButtonElement>(".tree-toggle")?.click();
    } else if (target.getAttribute("aria-expanded") === "true") focus(index + 1);
  } else if (event.key === "ArrowLeft") {
    if (target.getAttribute("aria-expanded") === "true") {
      target.closest(".tree-row")?.querySelector<HTMLButtonElement>(".tree-toggle")?.click();
    } else {
      const level = Number(target.getAttribute("aria-level"));
      for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
        if (Number(items[cursor].getAttribute("aria-level")) === level - 1) { focus(cursor); break; }
      }
    }
  }
}

async function openWorkResource(slug: string, name: string, kind: "artifacts" | "plan-stages", toast: (message: string) => void) {
  try {
    const response = await fetch(`/api/work/${encodeRef(slug)}/${kind}/${encodeRef(name)}/open`, {
      method: "POST", headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    if (response.status === 204) { toast("Opened artifact"); return; }
    const payload = await response.json() as { url?: string };
    if (payload.url) window.open(payload.url, "_blank", "noopener");
  } catch (error) { toast(`Could not open artifact: ${error instanceof Error ? error.message : String(error)}`); }
}

function asWarnings(data: JsonRecord | null): string[] {
  return Array.isArray(data?.warnings) ? data.warnings.filter((item): item is string => typeof item === "string") : [];
}

function FilterControls({ axis, registeredTags, statusFilter, setStatusFilter, kindFilter, setKindFilter, tagFilter, setTagFilter }:
  { axis: Axis; registeredTags: string[]; statusFilter: Record<string, boolean>; setStatusFilter: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
    kindFilter: string[]; setKindFilter: (value: string[]) => void; tagFilter: string[]; setTagFilter: (value: string[]) => void }) {
  if (axis === "capabilities") return null;
  const facet = axis === "taxonomy" ? { label: "Kind", options: ["Feature", "Vocabulary"], value: kindFilter, set: setKindFilter }
    : { label: "Tags", options: registeredTags, value: tagFilter, set: setTagFilter };
  return <div className="status-filters" role="group" aria-label="Filters">
    {axis === "work" && WORK_STATUSES.map((status) => <button type="button" key={status}
      className={`status-toggle st-${status}${statusFilter[status] ? " on" : ""}`} aria-pressed={statusFilter[status]}
      onClick={() => setStatusFilter((old) => ({ ...old, [status]: !old[status] }))}>{status}</button>)}
    <details className="facet" key={axis}><summary>{facet.label}{facet.value.length ? ` (${facet.value.length})` : ""}</summary>
      <div className="facet-panel">{facet.options.length ? facet.options.map((option) => <label className="facet-option" key={option}>
        <input type="checkbox" checked={facet.value.includes(option)} onChange={(event) => facet.set(event.target.checked
          ? [...facet.value, option] : facet.value.filter((value) => value !== option))} /> {option}</label>) : <div className="facet-empty">none available</div>}</div>
    </details>
  </div>;
}

function DetailView({ axis, detail, onEdit, onResource, onOpen, onDeletePlanStage, onAction }:
  { axis: Axis; detail: Detail; onEdit: () => void; onResource: (kind: "artifacts" | "sidecars" | "plan-stages", slug: string, name: string) => void;
    onOpen: (slug: string, name: string, kind?: "artifacts" | "plan-stages") => void;
    onDeletePlanStage: (slug: string, name: string, revision?: string) => void;
    onAction: (action: "start" | "complete" | "drop") => void }) {
  if (axis === "work") {
    const payload = detail as WorkDetail; const item = payload.item;
    return <><div className="detail-head"><div><h2>{item.title ?? item.slug}</h2><p className="item-meta">{item.slug}</p></div>
      <div className="detail-actions"><span className="badge">{item.status}</span><button className="edit-btn" type="button" onClick={onEdit}>Edit</button></div></div>
      <div className="action-buttons">{item.status === "backlog" && <><button className="action-btn start" type="button" onClick={() => onAction("start")}>Start</button>
        <button className="action-btn drop" type="button" onClick={() => onAction("drop")}>Drop</button></>}
        {item.status === "active" && <button className="action-btn complete" type="button" onClick={() => onAction("complete")}>Complete</button>}</div>
      <Fields><Field name="Priority" value={item.priority} /><Field name="Effort" value={item.effort} />
        <Field name="Complexity" value={item.complexity} /><Field name="Tags" value={item.tags?.join(", ") || "-"} />
        <Field name="Resolution" value={item.resolution} /><Field name="Blocked by" value={item.blocked_by?.map((b) => b.slug ?? b.external).join(", ") || "-"} />
        {item.parent && <Field name="Parent" value={item.parent} />}{item.initiative && <Field name="Initiative" value={item.initiative} />}</Fields>
      <div className="artifacts">{payload.artifacts.filter((resource) => resource.present && resource.name !== "initial-request").map((resource) =>
        <div className="artifact-group" key={resource.name}><button className="artifact" type="button" onClick={() => onOpen(item.slug, resource.name)}>{resource.name}</button>
          <button className="artifact-edit" type="button" aria-label={`Edit ${resource.name}`} onClick={() => onResource("artifacts", item.slug, resource.name)}>✎</button></div>)}</div>
      {payload.planStages?.length > 0 && <div className="plan-stages"><h3>Plan stages</h3>
        {payload.planStages.map((stage) => <div className="plan-stage" key={stage.id}>
          <div><strong>{stage.title}</strong><span className="item-meta"> {stage.id}</span></div>
          <div className="item-meta">Depends on: {stage.depends_on.length ? stage.depends_on.join(", ") : "none"}
            {stage.effort && ` · effort ${stage.effort}`}{stage.complexity && ` · complexity ${stage.complexity}`}
            {stage.priority != null && ` · priority ${stage.priority}`}{stage.tags.length > 0 && ` · ${stage.tags.join(", ")}`}</div>
          {payload.planStages.filter((candidate) => candidate.id !== stage.id
            && JSON.stringify(candidate.depends_on) === JSON.stringify(stage.depends_on)).length > 0
            && <div className="item-meta">Parallel with: {payload.planStages.filter((candidate) => candidate.id !== stage.id
              && JSON.stringify(candidate.depends_on) === JSON.stringify(stage.depends_on)).map((candidate) => candidate.id).join(", ")}</div>}
          <div className="artifact-group"><span>{stage.present ? "Document present" : "Document missing"}</span>
            {stage.present && <button type="button" onClick={() => onOpen(item.slug, stage.id, "plan-stages")}>Open</button>}
            <button type="button" onClick={() => onResource("plan-stages", item.slug, stage.id)}>{stage.present ? "Edit" : "Create"}</button>
            {stage.present && <button type="button" onClick={() => onDeletePlanStage(item.slug, stage.id, stage.revision)}>Delete</button>}</div>
        </div>)}</div>}
      {payload.sidecars?.some((resource) => resource.present) && <div className="sidecars-section"><h3>Sidecars</h3>
        {payload.sidecars.filter((resource) => resource.present).map((resource) => <div className="sidecar-item" key={resource.name}><span className="sidecar-name">{resource.name}</span>
          <button className="sidecar-edit-btn" type="button" onClick={() => onResource("sidecars", item.slug, resource.name)}>Edit</button></div>)}</div>}
      <Markdown source={item.body ?? ""} resolveLinks /></>;
  }
  if (axis === "taxonomy") {
    const term = (detail as TaxonomyDetail).term;
    return <><div className="detail-head"><div><h2>{term.name ?? term.slug}</h2><p className="item-meta">{term.qualified ?? term.slug}</p></div>
      <div className="detail-actions"><span className="badge">{term.kind}</span><button className="edit-btn" type="button" onClick={onEdit}>Edit</button></div></div>
      <Fields><Field name="Kind" value={term.kind} /><Field name="Origin" value={term.origin} /><Field name="Parent" value={term.parent} />
        <Field name="Relates to" value={term.relates_to?.join(", ") || "-"} /><Field name="Vocabulary" value={term.vocabulary?.join(", ") || "-"} /></Fields>
      <Markdown source={term.description ?? ""} resolveLinks /></>;
  }
  const capability = (detail as CapabilityDetail).capability;
  return <><div className="detail-head"><div><h2>{capability.name ?? capability.path}</h2><p className="item-meta">{capability.path}</p></div>
    <div className="detail-actions"><span className="badge">{capability.status}</span><button className="edit-btn" type="button" onClick={onEdit}>Edit</button></div></div>
    <Fields>{Object.entries(capability.fields ?? {}).map(([name, value]) => <Field name={name} value={Array.isArray(value) ? value.join(", ") : value} key={name} />)}</Fields>
    <Markdown source={capability.body ?? ""} resolveLinks /></>;
}

function EditorView({ editor, setDraft, saving, errors, conflict, registeredTags, data, onSave, onCancel, onRefreshConflict }:
  { editor: Editor; setDraft: (key: string, value: unknown) => void; saving: boolean; errors: string[]; conflict: unknown;
    registeredTags: string[]; data: Data; onSave: () => void; onCancel: () => void; onRefreshConflict: () => void }) {
  if (editor.mode === "resource") return <div className={`editor-container${saving ? " saving" : ""}`}>
    <EditorHeader title={`Edit ${editor.kind === "artifacts" ? "Artifact" : editor.kind === "sidecars" ? "Sidecar" : "Plan stage"}: ${editor.name}`} saving={saving} onSave={onSave} onCancel={onCancel} />
    <Errors errors={errors} />{Boolean(conflict) && <Conflict onRefresh={onRefreshConflict} onDiscard={onCancel} />}
    <MarkdownEditor value={editor.draft} onChange={(value) => setDraft("draft", value)} /></div>;
  const draft = editor.draft;
  return <div className={`editor-container${saving ? " saving" : ""}`}>
    <EditorHeader title={`${editor.mode === "create" ? "Create" : "Edit"} ${LABELS[editor.axis]}`} saving={saving} onSave={onSave} onCancel={onCancel} />
    <Errors errors={errors} />{Boolean(conflict) && <Conflict onRefresh={onRefreshConflict} onDiscard={onCancel} />}
    <div className="editor-section">Fields</div><div className="editor-fields">
      {editor.axis === "work" && <WorkFields draft={draft} setDraft={setDraft} registeredTags={registeredTags} data={data} current={editor.mode === "core" ? editor.ref : undefined} />}
      {editor.axis === "taxonomy" && <TaxonomyFields draft={draft} setDraft={setDraft} creating={editor.mode === "create"} data={data} current={editor.mode === "core" ? editor.ref : undefined} />}
      {editor.axis === "capabilities" && <CapabilityFields draft={draft} setDraft={setDraft} creating={editor.mode === "create"} data={data} current={editor.mode === "core" ? editor.ref : undefined} />}
    </div><div className="editor-section">Body</div>
    <MarkdownEditor value={String(draft.body ?? "")} onChange={(value) => setDraft("body", value)} />
  </div>;
}

function EditorHeader({ title, saving, onSave, onCancel }:
  { title: string; saving: boolean; onSave: () => void; onCancel: () => void }) {
  return <div className="editor-header"><div className="editor-title">{title}</div><div className="editor-actions">
    <button className="cancel-btn" type="button" onClick={onCancel}>Cancel</button><button className="save-btn" type="button" disabled={saving} onClick={onSave}>{saving ? "Saving..." : "Save"}</button>
  </div></div>;
}

function Conflict({ onRefresh, onDiscard }: { onRefresh: () => void; onDiscard: () => void }) {
  return <div className="conflict-banner"><strong>Stale write detected</strong><p>The server version changed. Your draft is preserved.</p>
    <button type="button" onClick={onRefresh}>Refresh from server</button><button type="button" onClick={onDiscard}>Discard draft</button></div>;
}

function optionsFor(field: TReferenceField, data: Data, current?: string, selected?: string[]) {
  return referenceOptions(field, { ...data, currentIdentifier: current, selected });
}

function WorkFields({ draft, setDraft, registeredTags, data, current }:
  { draft: Draft; setDraft: (key: string, value: unknown) => void; registeredTags: string[]; data: Data; current?: string }) {
  const tags = (draft.tags as string[] | undefined) ?? [];
  return <><TextInput label="Title" value={String(draft.title ?? "")} onChange={(value) => setDraft("title", value)} />
    <TextInput label="Priority" type="number" value={String(draft.priority ?? "")} onChange={(value) => setDraft("priority", value)} />
    <SelectInput label="Effort" value={String(draft.effort ?? "")} options={["", "low", "medium", "high", "very-high"]} onChange={(value) => setDraft("effort", value)} />
    <SelectInput label="Complexity" value={String(draft.complexity ?? "")} options={["", "low", "medium", "high", "very-high"]} onChange={(value) => setDraft("complexity", value)} />
    <ReferenceInput label="Parent" value={String(draft.parent ?? "")} options={optionsFor("work-parent", data, current)} onChange={(value) => setDraft("parent", value)} />
    <ReferenceInput label="Initiative" value={String(draft.initiative ?? "")} options={optionsFor("work-initiative", data, current)} onChange={(value) => setDraft("initiative", value)} />
    <ReferenceInput label="Blockers" multiple value={(draft.blockers as string[] | undefined) ?? []} options={optionsFor("work-blockers", data, current, (draft.blockers as string[] | undefined) ?? [])} onChange={(value) => setDraft("blockers", value)} />
    <div className="field-group"><label>Tags</label><div className="tag-checkboxes">{[...new Set([...registeredTags, ...tags])].map((tag) => <label className={`tag-checkbox${registeredTags.includes(tag) ? "" : " tag-stale"}`} key={tag}>
      <input type="checkbox" checked={tags.includes(tag)} onChange={(event) => setDraft("tags", event.target.checked ? [...tags, tag] : tags.filter((item) => item !== tag))} /> {tag}{registeredTags.includes(tag) ? "" : " (unregistered)"}</label>)}</div></div></>;
}

function TaxonomyFields({ draft, setDraft, creating, data, current }:
  { draft: Draft; setDraft: (key: string, value: unknown) => void; creating: boolean; data: Data; current?: string }) {
  return <><TextInput label="Name" value={String(draft.name ?? "")} onChange={(value) => setDraft("name", value)} />
    <SelectInput label="Kind" value={String(draft.kind ?? "Vocabulary")} options={["Vocabulary", "Feature"]} onChange={(value) => setDraft("kind", value)} />
    {creating && <><TextInput label="Slug" value={String(draft.slug ?? "")} onChange={(value) => setDraft("slug", value)} />
      <ReferenceInput label="Parent" value={String(draft.parent ?? "")} options={optionsFor("taxonomy-parent", data, current)} onChange={(value) => setDraft("parent", value)} /></>}
    {!creating && <ReferenceInput label="Relates to" multiple value={(draft.relates_to as string[] | undefined) ?? []} options={optionsFor("taxonomy-relates", data, current, (draft.relates_to as string[] | undefined) ?? [])} onChange={(value) => setDraft("relates_to", value)} />}
    <ReferenceInput label="Vocabulary" multiple value={(draft.vocabulary as string[] | undefined) ?? []} options={optionsFor("taxonomy-vocabulary", data, current, (draft.vocabulary as string[] | undefined) ?? [])} onChange={(value) => setDraft("vocabulary", value)} /></>;
}

function CapabilityFields({ draft, setDraft, creating, data, current }:
  { draft: Draft; setDraft: (key: string, value: unknown) => void; creating: boolean; data: Data; current?: string }) {
  if (creating) return <><TextInput label="Path" value={String(draft.path ?? "")} placeholder="e.g. web/editing" onChange={(value) => setDraft("path", value)} />
    <TextInput label="Name" value={String(draft.name ?? "")} onChange={(value) => setDraft("name", value)} />
    <SelectInput label="Status" value={String(draft.status ?? "Missing")} options={["Supported", "Partial", "Missing", "Blocked", "Omitted"]} onChange={(value) => setDraft("status", value)} /></>;
  const fields: Partial<Record<string, { field: TReferenceField; multiple?: boolean; negated?: boolean }>> = {
    Feature: { field: "capability-feature" }, Subject: { field: "capability-subject", multiple: true },
    Roles: { field: "capability-roles", multiple: true }, When: { field: "capability-when", multiple: true, negated: true },
    "Blocked by": { field: "capability-blocked-by" }, "Planning doc": { field: "capability-planning-doc" },
    "Superseded by": { field: "capability-superseded-by" },
  };
  return <>{CAPABILITY_FIELDS.map(([label, selectOptions]) => {
    if (selectOptions) return <SelectInput label={label} value={String(draft[label] ?? "")} options={selectOptions} onChange={(value) => setDraft(label, value)} key={label} />;
    const config = fields[label];
    if (!config) return <TextInput label={label} value={String(draft[label] ?? "")} onChange={(value) => setDraft(label, value)} key={label} />;
    const fieldValue = config.multiple ? (Array.isArray(draft[label]) ? draft[label] as string[] : String(draft[label] ?? "").split(",").map((item) => item.trim()).filter(Boolean)) : String(draft[label] ?? "");
    return <ReferenceInput key={label} label={label} value={fieldValue} multiple={config.multiple} negated={config.negated}
      options={optionsFor(config.field, data, current, Array.isArray(fieldValue) ? fieldValue.map((item) => item.replace(/^!/, "")) : undefined)} onChange={(value) => setDraft(label, value)} />;
  })}</>;
}

function StartModal({ onClose, onStart, errors }:
  { onClose: () => void; onStart: (force: boolean) => Promise<boolean>; errors: string[] }) {
  const [failed, setFailed] = useState(false);
  return <Modal title="Start Work Item" onClose={onClose}><Errors errors={errors} />
    {failed && <p>This item may have unresolved blockers. You can force-start it.</p>}
    <div className="modal-actions"><button type="button" onClick={onClose}>Cancel</button>
      <button className="save-btn" type="button" onClick={() => void onStart(failed).then((ok) => { if (!ok) setFailed(true); })}>{failed ? "Start (force)" : "Start"}</button></div></Modal>;
}

function CompleteModal({ detail, onClose, onComplete, errors }:
  { detail: WorkDetail; onClose: () => void; onComplete: (options: JsonRecord) => Promise<boolean>; errors: string[] }) {
  const checklist = detail.dodChecklist?.length ? detail.dodChecklist : ["tests pass", "docs synced", "capabilities reconciled", "reviewed", "version offered"];
  const [checked, setChecked] = useState<string[]>([]); const [resolution, setResolution] = useState(""); const [force, setForce] = useState(false);
  return <Modal title="Complete Work Item" onClose={onClose}><Errors errors={errors} />
    <div className="reconciliation-reminder"><strong>Reconciliation reminder</strong><br />Reconcile the capabilities ledger before completing.</div>
    <SelectInput label="Resolution" value={resolution} options={["", "done", "wontfix", "duplicate", "superseded"]} onChange={setResolution} />
    <h3>Definition of Done</h3><div className="dod-list">{checklist.map((item) => <label className="dod-item" key={item}>
      <input type="checkbox" checked={checked.includes(item)} onChange={(event) => setChecked(event.target.checked ? [...checked, item] : checked.filter((value) => value !== item))} /> {item}</label>)}</div>
    {force && <p className="modal-error">Completion was blocked. You can retry while ignoring blockers.</p>}
    <div className="modal-actions"><button type="button" onClick={onClose}>Cancel</button><button className="save-btn" type="button"
      disabled={!resolution || checked.length !== checklist.length} onClick={() => void onComplete({ resolution, dod_ack: checked, force }).then((ok) => { if (!ok) setForce(true); })}>{force ? "Complete (ignore blockers)" : "Complete"}</button></div>
  </Modal>;
}
