import {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
    type CSSProperties,
    type KeyboardEvent as ReactKeyboardEvent,
} from "react"
import {
    AlertDialog,
    Button,
    Callout,
    Card,
    Flex,
    Heading,
    IconButton,
    ScrollArea,
    Text,
    TextField,
} from "@radix-ui/themes"
import { useBeforeUnload, useLocation, useNavigate } from "react-router"
import { encodeRef, fetchJson, requestJson } from "../model/api"
import {
    buildPathTree,
    buildWorkTree,
    pathAncestors,
    pruneTree,
    workAncestors,
} from "../model/tree"
import {
    CompleteModal,
    DetailView,
    EditorView,
    FilterControls,
    StartModal,
} from "./content-views"
import { SettingsControl, Tree } from "./shared-components"
import { beginResize, loadExpanded } from "./ui-state"
import { AXES, LABELS, itemKey, parsePath, pathFor } from "./route-utils"
import { openWorkResource } from "./work-resource"
import type {
    TClientData as Data,
    TDetail as Detail,
    TDraft as Draft,
    TEditorSession as Editor,
} from "./ui-types"

const WORK_STATUSES = ["backlog", "active", "completed"]
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
} from "../model/types"

export function App() {
    const location = useLocation()
    const navigate = useNavigate()
    const initialRoute = useRef(parsePath(location.pathname)).current
    const [axis, setAxis] = useState<Axis>(initialRoute.axis)
    const [selected, setSelected] = useState<string | null>(initialRoute.key)
    const [data, setData] = useState<Data>({
        work: [],
        taxonomy: [],
        capabilities: [],
    })
    const [registeredTags, setRegisteredTags] = useState<string[]>([])
    const [filter, setFilter] = useState("")
    const [statusFilter, setStatusFilter] = useState<Record<string, boolean>>({
        backlog: true,
        active: true,
        completed: false,
    })
    const [kindFilter, setKindFilter] = useState<string[]>([])
    const [tagFilter, setTagFilter] = useState<string[]>([])
    const [expanded, setExpanded] =
        useState<Record<Axis, Set<string>>>(loadExpanded)
    const [seenPaths, setSeenPaths] = useState<Record<Axis, Set<string>>>(
        () => ({
            work: new Set(),
            taxonomy: new Set(),
            capabilities: new Set(),
        })
    )
    const [listWidth, setListWidth] = useState(() => {
        const stored = Number.parseFloat(
            localStorage.getItem("tcw.listWidth") ?? ""
        )
        return Number.isFinite(stored) && stored >= 0.12 && stored <= 0.6
            ? stored
            : 0.28
    })
    const [detail, setDetail] = useState<Detail | null>(null)
    const [loadingDetail, setLoadingDetail] = useState(false)
    const [editor, setEditor] = useState<Editor | null>(null)
    const [dirty, setDirty] = useState(false)
    const [saving, setSaving] = useState(false)
    const [errors, setErrors] = useState<string[]>([])
    const [conflict, setConflict] = useState<unknown>(null)
    const [warnings, setWarnings] = useState<string[]>([])
    const [toast, setToast] = useState("")
    const [modal, setModal] = useState<"drop" | "start" | "complete" | null>(
        null
    )
    const [loadError, setLoadError] = useState("")

    const showToast = useCallback((message: string) => {
        setToast(message)
        window.setTimeout(() => setToast(""), 2800)
    }, [])
    const showSaveResult = useCallback(
        (message: string, response: JsonRecord | null) => {
            const findings = asWarnings(response)
            setWarnings(findings)
            showToast(
                findings.length
                    ? `${message} with ${findings.length} validation issue${findings.length === 1 ? "" : "s"}`
                    : message
            )
        },
        [showToast]
    )
    const confirmLeave = useCallback(
        () =>
            !dirty ||
            window.confirm("You have unsaved changes. Leave without saving?"),
        [dirty]
    )
    useBeforeUnload(
        useCallback(
            (event) => {
                if (dirty) event.preventDefault()
            },
            [dirty]
        )
    )

    const load = useCallback(async (preserveSelection = true) => {
        try {
            const [work, taxonomy, capabilities, tags] = await Promise.all([
                fetchJson<WorkItem[]>("/api/work"),
                fetchJson<TaxonomyItem[]>("/api/taxonomy"),
                fetchJson<CapabilityItem[]>("/api/capabilities"),
                fetchJson<{ tags: string[] }>("/api/work/tags").catch(() => ({
                    tags: [],
                })),
            ])
            setData({ work, taxonomy, capabilities })
            setRegisteredTags(tags.tags ?? [])
            if (!preserveSelection) setSelected(null)
            setLoadError("")
        } catch (error) {
            setLoadError(error instanceof Error ? error.message : String(error))
        }
    }, [])

    useEffect(() => {
        void load()
    }, [load])
    useEffect(() => {
        localStorage.setItem(
            "tcw.treeExpanded",
            JSON.stringify(
                Object.fromEntries(
                    AXES.map((candidate) => [
                        candidate,
                        [...expanded[candidate]],
                    ])
                )
            )
        )
    }, [expanded])
    useEffect(() => {
        localStorage.setItem("tcw.listWidth", String(listWidth))
    }, [listWidth])
    useEffect(() => {
        const route = parsePath(location.pathname)
        if (route.axis !== axis || route.key !== selected) {
            if (!confirmLeave()) {
                navigate(pathFor(axis, selected), { replace: true })
                return
            }
            setEditor(null)
            setDirty(false)
            setDetail(null)
            setAxis(route.axis)
            setSelected(route.key)
        }
    }, [location.pathname]) // eslint-disable-line react-hooks/exhaustive-deps

    const currentItems = data[axis] as AxisItem[]
    useEffect(() => {
        if (
            !selected ||
            !(data[axis] as AxisItem[]).some(
                (item) => itemKey(axis, item) === selected
            )
        ) {
            setDetail(null)
            return
        }
        setLoadingDetail(true)
        const path =
            axis === "work"
                ? `/api/work/${encodeRef(selected)}`
                : axis === "taxonomy"
                  ? `/api/taxonomy/${encodeRef(selected)}`
                  : `/api/capabilities/${encodeRef(selected)}`
        void fetchJson<Detail>(path)
            .then(setDetail)
            .catch((error) => setLoadError(String(error)))
            .finally(() => setLoadingDetail(false))
    }, [axis, selected, data])

    const navigateTo = (nextAxis: Axis, key: string | null) => {
        if (!confirmLeave()) return
        setEditor(null)
        setDirty(false)
        setErrors([])
        setConflict(null)
        setDetail(null)
        setAxis(nextAxis)
        setSelected(key)
        navigate(pathFor(nextAxis, key))
        if (key) {
            const ancestors =
                nextAxis === "work"
                    ? workAncestors(key, data.work)
                    : pathAncestors(key)
            setExpanded((old) => ({
                ...old,
                [nextAxis]: new Set([...old[nextAxis], ...ancestors]),
            }))
        }
    }

    const updateFilter = (value: string) => {
        if (editor && !confirmLeave()) return
        setEditor(null)
        setDirty(false)
        setFilter(value)
        navigateTo(axis, null)
    }

    const visible = useCallback(
        (item: AxisItem) => {
            if (axis === "work") {
                const work = item as WorkItem
                if (work.status && statusFilter[work.status] === false)
                    return false
                if (
                    tagFilter.length &&
                    !tagFilter.some((tag) => work.tags?.includes(tag))
                )
                    return false
            }
            if (
                axis === "taxonomy" &&
                kindFilter.length &&
                !kindFilter.includes((item as TaxonomyItem).kind ?? "")
            )
                return false
            return (
                !filter ||
                JSON.stringify(item)
                    .toLowerCase()
                    .includes(filter.toLowerCase())
            )
        },
        [axis, filter, kindFilter, statusFilter, tagFilter]
    )

    const tree = useMemo(() => {
        const built =
            axis === "work"
                ? buildWorkTree(data.work)
                : buildPathTree(currentItems, (item) => itemKey(axis, item))
        const filtering = Boolean(
            filter ||
            kindFilter.length ||
            tagFilter.length ||
            (axis === "work" &&
                WORK_STATUSES.some((status) => !statusFilter[status]))
        )
        if (!filtering)
            return {
                nodes: built as Array<TreeNode<AxisItem>>,
                forced: new Set<string>(),
            }
        const pruned = pruneTree(built as Array<TreeNode<AxisItem>>, visible)
        return {
            nodes: pruned.nodes,
            forced: filter ? pruned.forceExpand : new Set<string>(),
        }
    }, [
        axis,
        currentItems,
        data.work,
        filter,
        kindFilter,
        statusFilter,
        tagFilter,
        visible,
    ])
    const effectiveExpanded = useMemo(
        () => new Set([...expanded[axis], ...tree.forced]),
        [axis, expanded, tree.forced]
    )
    useEffect(() => {
        const parents: string[] = []
        const collect = (nodes: Array<TreeNode<AxisItem>>) =>
            nodes.forEach((node) => {
                if (node.children.length) {
                    parents.push(node.path)
                    collect(node.children)
                }
            })
        collect(tree.nodes)
        const unseen = parents.filter((path) => !seenPaths[axis].has(path))
        if (!unseen.length) return
        setSeenPaths((old) => ({
            ...old,
            [axis]: new Set([...old[axis], ...unseen]),
        }))
        setExpanded((old) => ({
            ...old,
            [axis]: new Set([...old[axis], ...unseen]),
        }))
    }, [axis, seenPaths, tree.nodes])

    const setDraft = (key: string, value: unknown) => {
        setEditor((current) => {
            if (!current) return current
            if (current.mode === "resource") {
                return key === "draft"
                    ? { ...current, draft: String(value) }
                    : current
            }
            return {
                ...current,
                draft: { ...current.draft, [key]: value },
            } as Editor
        })
        setDirty(true)
    }

    const enterCreate = () => {
        const draft =
            axis === "work"
                ? {
                      title: "",
                      priority: "",
                      effort: "",
                      complexity: "",
                      parent: "",
                      initiative: "",
                      blockers: [],
                      tags: [],
                      body: "",
                  }
                : axis === "taxonomy"
                  ? {
                        name: "",
                        kind: "Vocabulary",
                        slug: "",
                        parent: "",
                        vocabulary: [],
                        description: "",
                        body: "",
                    }
                  : { path: "", name: "", status: "Missing", body: "" }
        setEditor({ mode: "create", axis, draft })
        setSelected(null)
        setDirty(false)
        setErrors([])
        setConflict(null)
    }

    const enterCore = () => {
        if (!detail) return
        let draft: Draft
        let ref: string
        let revision: string
        if (axis === "work") {
            const payload = detail as WorkDetail
            const item = payload.item
            draft = {
                title: item.title ?? "",
                priority: item.priority ?? "",
                effort: item.effort ?? "",
                complexity: item.complexity ?? "",
                parent: item.parent ?? "",
                initiative: item.initiative ?? "",
                blockers: (item.blocked_by ?? [])
                    .map((blocker) => blocker.slug ?? blocker.external ?? "")
                    .filter(Boolean),
                tags: item.tags ?? [],
                body: item.body ?? "",
            }
            ref = item.slug
            revision = payload.coreRevision
        } else if (axis === "taxonomy") {
            const payload = detail as TaxonomyDetail
            const term = payload.term
            draft = {
                name: term.name ?? "",
                kind: term.kind ?? "Vocabulary",
                relates_to: term.relates_to ?? [],
                vocabulary: term.vocabulary ?? [],
                body: term.description ?? "",
            }
            ref = term.qualified ?? term.slug
            revision = payload.coreRevision
        } else {
            const payload = detail as CapabilityDetail
            const capability = payload.capability
            draft = {
                ...(capability.fields ?? {}),
                body: capability.body ?? "",
            }
            ref = capability.path
            revision = payload.coreRevision
        }
        setEditor({
            mode: "core",
            axis,
            ref,
            revision,
            draft,
            original: structuredClone(draft),
        })
        setDirty(false)
        setErrors([])
        setConflict(null)
    }

    const enterResource = async (
        kind: "artifacts" | "sidecars" | "plan-stages",
        slug: string,
        name: string
    ) => {
        try {
            const resource = await fetchJson<ResourceDetail>(
                `/api/work/${encodeRef(slug)}/${kind}/${encodeRef(name)}`
            )
            setEditor({
                mode: "resource",
                axis: "work",
                kind,
                slug,
                name,
                revision: resource.revision,
                mediaType:
                    resource.mediaType ??
                    (kind === "artifacts"
                        ? "text/markdown"
                        : "application/yaml"),
                draft: resource.content,
                original: resource.content,
            })
            setDirty(false)
            setErrors([])
            setConflict(null)
        } catch (error) {
            if (kind === "plan-stages") {
                const draft =
                    "## Objective\n\n\n\n## Pre-stage checks\n\n\n\n## Implementation\n\n\n\n## Post-stage checks\n\n"
                setEditor({
                    mode: "resource",
                    axis: "work",
                    kind,
                    slug,
                    name,
                    revision: "",
                    mediaType: "text/markdown",
                    draft,
                    original: "",
                })
                setDirty(false)
                setErrors([])
                setConflict(null)
                return
            }
            showToast(
                `Failed to load ${kind === "artifacts" ? "artifact" : "sidecar"}: ${String(error)}`
            )
        }
    }

    const cancelEditor = () => {
        if (dirty && !window.confirm("You have unsaved changes. Discard them?"))
            return
        setEditor(null)
        setDirty(false)
        setErrors([])
        setConflict(null)
    }

    const save = async () => {
        if (!editor || saving) return
        setSaving(true)
        setErrors([])
        setConflict(null)
        try {
            if (editor.mode === "create") {
                const draft = editor.draft
                let path: string
                let body: JsonRecord
                if (editor.axis === "work") {
                    if (!String(draft.title ?? "").trim()) {
                        setErrors(["Title is required"])
                        return
                    }
                    path = "/api/work"
                    body = compact({
                        title: String(draft.title).trim(),
                        priority:
                            draft.priority === ""
                                ? undefined
                                : Number(draft.priority),
                        effort: draft.effort,
                        complexity: draft.complexity,
                        parent: draft.parent,
                        initiative: draft.initiative,
                        blockers: draft.blockers,
                        tags: draft.tags,
                        body: draft.body,
                    })
                } else if (editor.axis === "taxonomy") {
                    if (!String(draft.name ?? "").trim()) {
                        setErrors(["Name is required"])
                        return
                    }
                    path = "/api/taxonomy"
                    body = compact({
                        name: String(draft.name).trim(),
                        kind: draft.kind,
                        slug: draft.slug,
                        parent: draft.parent,
                        vocabulary: draft.vocabulary,
                        description: draft.body,
                    })
                } else {
                    if (!String(draft.path ?? "").trim()) {
                        setErrors(["Path is required"])
                        return
                    }
                    path = "/api/capabilities"
                    body = compact({
                        path: String(draft.path).trim(),
                        name: draft.name,
                        status: draft.status,
                        body: draft.body,
                    })
                }
                const result = await requestJson<JsonRecord>(path, "POST", body)
                if (!result.ok) {
                    setErrors([
                        result.error || `Create failed (${result.status})`,
                    ])
                    return
                }
                showSaveResult(`${LABELS[editor.axis]} created`, result.data)
            } else if (editor.mode === "core") {
                const fields: JsonRecord = {}
                for (const [key, value] of Object.entries(editor.draft)) {
                    if (
                        key !== "body" &&
                        JSON.stringify(value) !==
                            JSON.stringify(editor.original[key])
                    )
                        fields[key] = value
                }
                if (editor.axis === "work" && "priority" in fields) {
                    fields.priority =
                        fields.priority === "" ? null : Number(fields.priority)
                }
                if (editor.axis === "capabilities") {
                    for (const key of [
                        "Feature",
                        "Blocked by",
                        "Planning doc",
                        "Superseded by",
                    ]) {
                        if (fields[key] === "") fields[key] = null
                    }
                }
                const body: JsonRecord = { revision: editor.revision, fields }
                if (editor.draft.body !== editor.original.body)
                    body.body = editor.draft.body
                const path =
                    editor.axis === "work"
                        ? `/api/work/${encodeRef(editor.ref)}`
                        : editor.axis === "taxonomy"
                          ? `/api/taxonomy/${encodeRef(editor.ref)}`
                          : `/api/capabilities/${encodeRef(editor.ref)}`
                const result = await requestJson<JsonRecord>(
                    path,
                    "PATCH",
                    body
                )
                if (result.status === 409) {
                    setConflict({ local: structuredClone(editor.draft) })
                    return
                }
                if (!result.ok) {
                    setErrors([
                        result.error || `Save failed (${result.status})`,
                    ])
                    return
                }
                showSaveResult("Saved", result.data)
            } else {
                const result = await requestJson<
                    ResourceDetail & TMutationResponse
                >(
                    `/api/work/${encodeRef(editor.slug)}/${editor.kind}/${encodeRef(editor.name)}`,
                    "PUT",
                    {
                        name: editor.name,
                        content: editor.draft,
                        mediaType: editor.mediaType,
                        revision: editor.revision,
                    }
                )
                if (result.status === 409) {
                    setConflict({ local: editor.draft })
                    return
                }
                if (!result.ok) {
                    setErrors([
                        result.error || `Save failed (${result.status})`,
                    ])
                    return
                }
                showSaveResult(
                    editor.kind === "artifacts"
                        ? "Artifact saved"
                        : "Sidecar saved",
                    result.data
                )
            }
            setEditor(null)
            setDirty(false)
            await load()
        } catch (error) {
            setErrors([error instanceof Error ? error.message : String(error)])
        } finally {
            setSaving(false)
        }
    }

    const refreshConflict = async () => {
        if (!editor) return
        if (
            !window.confirm(
                "Replace your draft with the current server version?"
            )
        )
            return
        setEditor(null)
        setDirty(false)
        setConflict(null)
        await load()
    }

    const doAction = async (
        action: "start" | "complete" | "drop",
        options: JsonRecord = {}
    ) => {
        if (!selected) return false
        const result =
            action === "drop"
                ? await requestJson<JsonRecord>(
                      `/api/work/${encodeRef(selected)}`,
                      "DELETE"
                  )
                : await requestJson<JsonRecord>(
                      `/api/work/${encodeRef(selected)}/actions/${action}`,
                      "POST",
                      options
                  )
        if (!result.ok) {
            setErrors([result.error || `${action} failed`])
            return false
        }
        setModal(null)
        showToast(
            `Work item ${action === "complete" ? "completed" : `${action}ed`}`
        )
        await load(action !== "drop")
        if (action === "drop") navigateTo("work", null)
        return true
    }

    const deletePlanStage = async (
        slug: string,
        name: string,
        revision?: string
    ) => {
        if (!window.confirm(`Delete plan stage ${name}?`)) return
        const response = await fetch(
            `/api/work/${encodeRef(slug)}/plan-stages/${encodeRef(name)}`,
            {
                method: "DELETE",
                headers: revision ? { "X-TCW-Revision": revision } : undefined,
            }
        )
        if (response.status === 409) {
            showToast("Plan stage changed; refresh before deleting")
            return
        }
        if (!response.ok) {
            showToast(`Could not delete plan stage: ${response.statusText}`)
            return
        }
        showToast("Plan stage deleted")
        await load()
    }

    return (
        <>
            <header className="topbar">
                <div>
                    <Heading as="h1" size="6">
                        TCW
                    </Heading>
                    <Text as="p" color="gray" size="2">
                        {data.taxonomy.length} taxonomy ·{" "}
                        {data.capabilities.length} capabilities ·{" "}
                        {data.work.length} work items
                    </Text>
                </div>
                <nav className="tabs" aria-label="TCW views">
                    {AXES.map((candidate) => (
                        <Button
                            type="button"
                            key={candidate}
                            className={`tab${axis === candidate ? " active" : ""}`}
                            variant={axis === candidate ? "solid" : "soft"}
                            onClick={() => navigateTo(candidate, null)}
                        >
                            {LABELS[candidate]}
                        </Button>
                    ))}
                    <SettingsControl />
                </nav>
            </header>
            <main
                className="shell"
                style={
                    { "--list-width": `${listWidth * 100}%` } as CSSProperties
                }
            >
                <section className="list-pane">
                    <div className="list-head">
                        <Heading as="h2" size="3">
                            {LABELS[axis]}
                        </Heading>
                        <TextField.Root
                            type="search"
                            placeholder="Filter"
                            value={filter}
                            onChange={(event) =>
                                updateFilter(event.target.value)
                            }
                        >
                            {filter && (
                                <TextField.Slot side="right">
                                    <IconButton
                                        type="button"
                                        size="1"
                                        variant="ghost"
                                        aria-label="Clear filter"
                                        onClick={() => updateFilter("")}
                                    >
                                        ×
                                    </IconButton>
                                </TextField.Slot>
                            )}
                        </TextField.Root>
                    </div>
                    <FilterControls
                        axis={axis}
                        registeredTags={registeredTags}
                        statusFilter={statusFilter}
                        setStatusFilter={setStatusFilter}
                        kindFilter={kindFilter}
                        setKindFilter={setKindFilter}
                        tagFilter={tagFilter}
                        setTagFilter={setTagFilter}
                    />
                    <div className="create-row">
                        <Button
                            className="create-btn"
                            variant="outline"
                            type="button"
                            onClick={enterCreate}
                        >
                            + Create {LABELS[axis]}
                        </Button>
                    </div>
                    <ScrollArea
                        className="list"
                        type="auto"
                        role="tree"
                        aria-label="Objects"
                        onKeyDown={handleTreeKeyboard}
                    >
                        {tree.nodes.length ? (
                            <Tree
                                nodes={tree.nodes}
                                axis={axis}
                                selected={selected}
                                expanded={effectiveExpanded}
                                visible={visible}
                                onSelect={(key) => navigateTo(axis, key)}
                                onToggle={(path) => {
                                    if (filter) return
                                    setExpanded((old) => {
                                        const next = new Set(old[axis])
                                        if (next.has(path)) next.delete(path)
                                        else next.add(path)
                                        return { ...old, [axis]: next }
                                    })
                                }}
                            />
                        ) : (
                            <Text className="empty" color="gray">
                                No {LABELS[axis].toLowerCase()} entries.
                            </Text>
                        )}
                    </ScrollArea>
                </section>
                <div
                    className="col-resizer"
                    role="separator"
                    aria-orientation="vertical"
                    aria-label="Resize list column"
                    onPointerDown={(event) =>
                        beginResize(
                            event,
                            event.currentTarget.parentElement!,
                            0.12,
                            0.6,
                            setListWidth
                        )
                    }
                />
                <section
                    className="detail-pane"
                    aria-live="polite"
                    onClick={(event) => {
                        const anchor = (
                            event.target as HTMLElement
                        ).closest<HTMLAnchorElement>("a[data-nav-key]")
                        if (anchor) {
                            event.preventDefault()
                            navigateTo(
                                anchor.dataset.navAxis as Axis,
                                anchor.dataset.navKey!
                            )
                        }
                    }}
                >
                    {warnings.length > 0 && (
                        <Callout.Root color="amber" role="alert">
                            <Callout.Text>
                                <strong>Saved with validation issues</strong>
                                <ul>
                                    {warnings.map((warning) => (
                                        <li key={warning}>{warning}</li>
                                    ))}
                                </ul>
                            </Callout.Text>
                        </Callout.Root>
                    )}
                    {loadError ? (
                        <>
                            <Text className="empty" color="gray">
                                Failed to load: {loadError}
                            </Text>
                            <Button
                                variant="soft"
                                type="button"
                                onClick={() => void load()}
                            >
                                Retry
                            </Button>
                        </>
                    ) : editor ? (
                        <EditorView
                            editor={editor}
                            setDraft={setDraft}
                            saving={saving}
                            errors={errors}
                            conflict={conflict}
                            registeredTags={registeredTags}
                            data={data}
                            onSave={() => void save()}
                            onCancel={cancelEditor}
                            onRefreshConflict={() => void refreshConflict()}
                        />
                    ) : loadingDetail ? (
                        <Text className="empty" color="gray">
                            Loading...
                        </Text>
                    ) : detail ? (
                        <DetailView
                            axis={axis}
                            detail={detail}
                            onEdit={enterCore}
                            onResource={(kind, slug, name) =>
                                void enterResource(kind, slug, name)
                            }
                            onOpen={(slug, name, kind = "artifacts") =>
                                void openWorkResource(
                                    slug,
                                    name,
                                    kind,
                                    showToast
                                )
                            }
                            onDeletePlanStage={(slug, name, revision) =>
                                void deletePlanStage(slug, name, revision)
                            }
                            onAction={(action) => setModal(action)}
                        />
                    ) : (
                        <Text className="empty" color="gray">
                            Select an entry.
                        </Text>
                    )}
                </section>
            </main>
            {toast && (
                <Card className="toast">
                    <Text size="2">{toast}</Text>
                </Card>
            )}
            {modal === "drop" && selected && (
                <AlertDialog.Root
                    open
                    onOpenChange={(open) => {
                        if (!open) setModal(null)
                    }}
                >
                    <AlertDialog.Content className="modal-box" maxWidth="480px">
                        <AlertDialog.Title>Drop Work Item</AlertDialog.Title>
                        <AlertDialog.Description size="2">
                            This permanently drops <strong>{selected}</strong>.
                        </AlertDialog.Description>
                        <Flex
                            className="modal-actions"
                            gap="3"
                            mt="4"
                            justify="end"
                        >
                            <AlertDialog.Cancel>
                                <Button variant="soft" color="gray">
                                    Cancel
                                </Button>
                            </AlertDialog.Cancel>
                            <AlertDialog.Action>
                                <Button
                                    color="red"
                                    onClick={() => void doAction("drop")}
                                >
                                    Drop
                                </Button>
                            </AlertDialog.Action>
                        </Flex>
                    </AlertDialog.Content>
                </AlertDialog.Root>
            )}
            {modal === "start" && (
                <StartModal
                    onClose={() => setModal(null)}
                    onStart={(force) =>
                        doAction("start", force ? { force: true } : {})
                    }
                    errors={errors}
                />
            )}
            {modal === "complete" && detail && (
                <CompleteModal
                    detail={detail as WorkDetail}
                    onClose={() => setModal(null)}
                    onComplete={(options) => doAction("complete", options)}
                    errors={errors}
                />
            )}
        </>
    )
}

function compact(record: JsonRecord): JsonRecord {
    return Object.fromEntries(
        Object.entries(record).filter(
            ([, value]) =>
                value !== undefined &&
                value !== "" &&
                (!Array.isArray(value) || value.length > 0)
        )
    )
}

function handleTreeKeyboard(event: ReactKeyboardEvent<HTMLDivElement>) {
    const target = (event.target as HTMLElement).closest<HTMLElement>(
        '[role="treeitem"]'
    )
    if (!target) return
    const keys = [
        "ArrowUp",
        "ArrowDown",
        "ArrowLeft",
        "ArrowRight",
        "Home",
        "End",
    ]
    if (!keys.includes(event.key)) return
    event.preventDefault()
    const items = [
        ...event.currentTarget.querySelectorAll<HTMLElement>(
            '[role="treeitem"]'
        ),
    ]
    const index = items.indexOf(target)
    const focus = (next: number) => items[next]?.focus()
    if (event.key === "ArrowUp") focus(index - 1)
    else if (event.key === "ArrowDown") focus(index + 1)
    else if (event.key === "Home") focus(0)
    else if (event.key === "End") focus(items.length - 1)
    else if (event.key === "ArrowRight") {
        if (target.getAttribute("aria-expanded") === "false") {
            target
                .closest(".tree-row")
                ?.querySelector<HTMLButtonElement>(".tree-toggle")
                ?.click()
        } else if (target.getAttribute("aria-expanded") === "true")
            focus(index + 1)
    } else if (event.key === "ArrowLeft") {
        if (target.getAttribute("aria-expanded") === "true") {
            target
                .closest(".tree-row")
                ?.querySelector<HTMLButtonElement>(".tree-toggle")
                ?.click()
        } else {
            const level = Number(target.getAttribute("aria-level"))
            for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
                if (
                    Number(items[cursor].getAttribute("aria-level")) ===
                    level - 1
                ) {
                    focus(cursor)
                    break
                }
            }
        }
    }
}

function asWarnings(data: JsonRecord | null): string[] {
    return Array.isArray(data?.warnings)
        ? data.warnings.filter(
              (item): item is string => typeof item === "string"
          )
        : []
}
