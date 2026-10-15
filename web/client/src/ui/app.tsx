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
    Button,
    Callout,
    Card,
    Flex,
    Heading,
    IconButton,
    Text,
    TextField,
} from "@radix-ui/themes"
import { useBeforeUnload, useLocation, useNavigate } from "react-router"
import {
    encodePath,
    encodeRef,
    fetchJson,
    findingLines,
    isStaleWrite,
    requestJson,
} from "../model/api"
import {
    buildPathTree,
    buildWorkTree,
    pathAncestors,
    pruneTree,
    sortWorkTree,
    workAncestors,
    type TSortDirection,
    type TWorkSortKey,
} from "../model/tree"
import {
    NO_STAGE,
    boardQuery,
    boardRows,
    defaultStageFilter,
    knownAssignees,
    needsAll,
    personName,
    stageShown,
} from "../model/work"
import {
    DetailView,
    EditorView,
    FacetPopover,
    SortControl,
} from "./content-views"
import { SettingsControl, Tree } from "./shared-components"
import { beginResize, loadExpanded } from "./ui-state"
import { AXES, LABELS, itemKey, parsePath, pathFor } from "./route-utils"
import type {
    TClientData as Data,
    TDetail as Detail,
    TDraft as Draft,
    TEditorSession as Editor,
} from "./ui-types"
import type {
    Axis,
    AxisItem,
    CapabilityDetail,
    CapabilityItem,
    JsonRecord,
    TBoard,
    TFileContent,
    TProject,
    TaxonomyDetail,
    TaxonomyItem,
    TreeNode,
    WorkDetail,
    WorkItem,
} from "../model/types"
import { WorkPage } from "./work-views"

type TBoardState = {
    people: Record<string, string>
    fallback: boolean
    unavailable?: string
}

export function App() {
    const location = useLocation()
    const navigate = useNavigate()
    const initialRoute = useRef(parsePath(location.pathname)).current
    const [axis, setAxis] = useState<Axis>(initialRoute.axis)
    const [selected, setSelected] = useState<string | null>(initialRoute.key)
    const [project, setProject] = useState<TProject | null>(null)
    const [data, setData] = useState<Data>({
        work: [],
        taxonomy: [],
        capabilities: [],
    })
    const [board, setBoard] = useState<TBoardState>({
        people: {},
        fallback: false,
    })
    const [filter, setFilter] = useState("")
    const [stageFilter, setStageFilter] = useState<Record<string, boolean>>({})
    const [tagFilter, setTagFilter] = useState<string[]>([])
    const [assigneeFilter, setAssigneeFilter] = useState<string[]>([])
    const [kindFilter, setKindFilter] = useState<string[]>([])
    const [workSortKey, setWorkSortKey] = useState<TWorkSortKey>("name")
    const [workSortDirection, setWorkSortDirection] =
        useState<TSortDirection>("ascending")
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
    const [workDetail, setWorkDetail] = useState<WorkDetail | null>(null)
    const [detailError, setDetailError] = useState("")
    const [detailVersion, setDetailVersion] = useState(0)
    const [loadingDetail, setLoadingDetail] = useState(false)
    const [editor, setEditor] = useState<Editor | null>(null)
    const [dirty, setDirty] = useState(false)
    const [saving, setSaving] = useState(false)
    const [errors, setErrors] = useState<string[]>([])
    const [conflict, setConflict] = useState<unknown>(null)
    const [warnings, setWarnings] = useState<string[]>([])
    const [toast, setToast] = useState("")
    const [loadError, setLoadError] = useState("")

    const showToast = useCallback((message: string) => {
        setToast(message)
        window.setTimeout(() => setToast(""), 2800)
    }, [])
    const showSaveResult = useCallback(
        (message: string, response: unknown) => {
            const findings = findingLines(response)
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

    const stages = useMemo(() => project?.stages ?? [], [project])
    const query = useMemo(
        () => boardQuery(needsAll(stageFilter, stages), tagFilter),
        [stageFilter, stages, tagFilter]
    )

    const loadProject = useCallback(async () => {
        const found = await fetchJson<TProject>("/api/project")
        setProject(found)
        setStageFilter((current) =>
            Object.keys(current).length
                ? current
                : defaultStageFilter(found.stages)
        )
        return found
    }, [])

    const loadBoard = useCallback(async (search: string) => {
        const found = await fetchJson<TBoard>(`/api/work${search}`)
        setData((old) => ({ ...old, work: boardRows(found) }))
        setBoard({
            people: found.people,
            fallback: found.fallback,
            unavailable: found.unavailable,
        })
    }, [])

    const loadRecords = useCallback(async (found: TProject) => {
        const [taxonomy, capabilities] = await Promise.all([
            found.axes.taxonomy
                ? fetchJson<TaxonomyItem[]>("/api/taxonomy")
                : Promise.resolve([]),
            found.axes.capabilities
                ? fetchJson<CapabilityItem[]>("/api/capabilities")
                : Promise.resolve([]),
        ])
        setData((old) => ({ ...old, taxonomy, capabilities }))
    }, [])

    const load = useCallback(async () => {
        try {
            const found = await loadProject()
            await loadRecords(found)
            setLoadError("")
        } catch (error) {
            setLoadError(error instanceof Error ? error.message : String(error))
        }
    }, [loadProject, loadRecords])

    // The board reloads when its query changes: a terminal stage ticked or
    // unticked, or the ticked tags, which the backend matches.
    const reloadBoard = useCallback(async () => {
        if (!project?.axes.work) return
        try {
            await loadBoard(query)
            setLoadError("")
        } catch (error) {
            setLoadError(error instanceof Error ? error.message : String(error))
        }
    }, [loadBoard, project, query])

    useEffect(() => {
        void load()
    }, [load])
    useEffect(() => {
        void reloadBoard()
    }, [reloadBoard])
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
            setWorkDetail(null)
            setAxis(route.axis)
            setSelected(route.key)
        }
    }, [location.pathname]) // eslint-disable-line react-hooks/exhaustive-deps

    // A work item is read by its folder whether or not the board holds it:
    // the filters may hide it, and a Jira key in the URL names it too. The
    // answer carries the folder, and a key is replaced by it.
    useEffect(() => {
        if (axis !== "work" || !selected) {
            setWorkDetail(null)
            return
        }
        let stale = false
        setLoadingDetail(true)
        setDetailError("")
        void fetchJson<WorkDetail>(`/api/work/${encodeRef(selected)}`)
            .then((found) => {
                if (stale) return
                setWorkDetail(found)
                if (found.folder !== selected) {
                    setSelected(found.folder)
                    navigate(pathFor("work", found.folder), { replace: true })
                }
            })
            .catch((error: unknown) => {
                if (stale) return
                setWorkDetail(null)
                setDetailError(
                    error instanceof Error ? error.message : String(error)
                )
            })
            .finally(() => {
                if (!stale) setLoadingDetail(false)
            })
        return () => {
            stale = true
        }
    }, [axis, selected, detailVersion]) // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        if (
            axis === "work" ||
            !selected ||
            !(data[axis] as AxisItem[]).some(
                (item) => itemKey(axis, item) === selected
            )
        ) {
            setDetail(null)
            return
        }
        setLoadingDetail(true)
        void fetchJson<Detail>(`/api/${axis}/${encodeRef(selected)}`)
            .then(setDetail)
            .catch((error) => setLoadError(String(error)))
            .finally(() => setLoadingDetail(false))
    }, [axis, selected, data])

    const readFile = useCallback(
        (path: string) =>
            fetchJson<TFileContent>(
                `/api/work/${encodeRef(selected ?? "")}/files/${encodePath(path)}`
            ),
        [selected]
    )

    const navigateTo = (nextAxis: Axis, key: string | null) => {
        if (!confirmLeave()) return
        setEditor(null)
        setDirty(false)
        setErrors([])
        setConflict(null)
        setDetail(null)
        setWorkDetail(null)
        setAxis(nextAxis)
        setSelected(key)
        navigate(pathFor(nextAxis, key))
        if (key) {
            const ancestors =
                nextAxis === "work"
                    ? workAncestors(
                          data.work.find(
                              (item) => itemKey("work", item) === key
                          )?.slug ?? "",
                          data.work
                      )
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
                if (!stageShown(work, stageFilter)) return false
                if (
                    assigneeFilter.length &&
                    !assigneeFilter.includes(work.assignee ?? "")
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
        [axis, assigneeFilter, filter, kindFilter, stageFilter]
    )

    const currentItems = data[axis] as AxisItem[]
    const tree = useMemo(() => {
        const built =
            axis === "work"
                ? sortWorkTree(
                      buildWorkTree(data.work),
                      workSortKey,
                      workSortDirection,
                      stages.map((row) => row.name),
                      project?.scales.priority ?? []
                  )
                : buildPathTree(currentItems, (item) => itemKey(axis, item))
        const filtering = Boolean(
            filter ||
            kindFilter.length ||
            (axis === "work" &&
                (assigneeFilter.length ||
                    Object.values(stageFilter).some((ticked) => !ticked)))
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
        assigneeFilter.length,
        currentItems,
        data.work,
        filter,
        kindFilter.length,
        project,
        stageFilter,
        stages,
        visible,
        workSortDirection,
        workSortKey,
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

    const stageKind = useMemo(
        () => new Map(stages.map((row) => [row.name, row.kind])),
        [stages]
    )
    const workRowClass = useCallback(
        (item: AxisItem) => {
            const work = item as WorkItem
            const kind = work.stage ? stageKind.get(work.stage) : undefined
            return `st-${work.unread || !kind ? "none" : kind}`
        },
        [stageKind]
    )

    const setDraft = (key: string, value: unknown) => {
        setEditor((current) =>
            current
                ? ({
                      ...current,
                      draft: { ...current.draft, [key]: value },
                  } as Editor)
                : current
        )
        setDirty(true)
    }

    const enterCreate = () => {
        if (axis === "work") return
        const draft =
            axis === "taxonomy"
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
        if (!detail || axis === "work") return
        let draft: Draft
        let ref: string
        let revision: string
        if (axis === "taxonomy") {
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
                if (editor.axis === "taxonomy") {
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
            } else {
                const fields: JsonRecord = {}
                for (const [key, value] of Object.entries(editor.draft)) {
                    if (
                        key !== "body" &&
                        JSON.stringify(value) !==
                            JSON.stringify(editor.original[key])
                    )
                        fields[key] = value
                }
                if (editor.axis === "capabilities") {
                    for (const key of [
                        "Feature",
                        "Blocked by",
                        "Superseded by",
                    ])
                        if (fields[key] === "") fields[key] = null
                }
                const body: JsonRecord = { revision: editor.revision, fields }
                if (editor.draft.body !== editor.original.body)
                    body.body = editor.draft.body
                const result = await requestJson<JsonRecord>(
                    `/api/${editor.axis}/${encodeRef(editor.ref)}`,
                    "PATCH",
                    body
                )
                if (isStaleWrite(result)) {
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
            }
            setEditor(null)
            setDirty(false)
            if (project) await loadRecords(project)
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
        if (project) await loadRecords(project)
    }

    const retryDetail = () => setDetailVersion((count) => count + 1)
    const kept = project ? project.axes[axis] : true
    const assignees = knownAssignees(data.work, project?.user ?? null)
    const people = { ...(project?.people ?? {}), ...board.people }

    return (
        <>
            <header className="topbar">
                <div>
                    <Heading as="h1" size="6">
                        TCW{project ? ` · ${project.id}` : ""}
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
                    {axis === "work" && project && (
                        <Flex
                            className="status-filters"
                            role="group"
                            aria-label="Filters"
                            align="center"
                            gap="2"
                            wrap="wrap"
                        >
                            <FacetPopover
                                label="Stage"
                                options={[
                                    ...stages.map((row) => row.name),
                                    ...(project.recordOwner === "backend"
                                        ? [NO_STAGE]
                                        : []),
                                ]}
                                value={Object.keys(stageFilter).filter(
                                    (name) => stageFilter[name]
                                )}
                                onChange={(ticked) =>
                                    setStageFilter(
                                        Object.fromEntries(
                                            [
                                                ...stages.map(
                                                    (row) => row.name
                                                ),
                                                NO_STAGE,
                                            ].map((name) => [
                                                name,
                                                ticked.includes(name) ||
                                                    (name === NO_STAGE &&
                                                        project.recordOwner !==
                                                            "backend"),
                                            ])
                                        )
                                    )
                                }
                            />
                            <FacetPopover
                                label="Tags"
                                options={project.tags}
                                value={tagFilter}
                                onChange={setTagFilter}
                            />
                            <FacetPopover
                                label="Assignee"
                                options={assignees}
                                value={assigneeFilter}
                                onChange={setAssigneeFilter}
                                display={(id) =>
                                    id === project.user
                                        ? `${personName(id, people)} (me)`
                                        : personName(id, people)
                                }
                            />
                            <SortControl
                                sortKey={workSortKey}
                                direction={workSortDirection}
                                onSortKeyChange={setWorkSortKey}
                                onDirectionChange={setWorkSortDirection}
                            />
                        </Flex>
                    )}
                    {axis === "taxonomy" && kept && (
                        <Flex
                            className="status-filters"
                            role="group"
                            aria-label="Filters"
                            align="center"
                            gap="2"
                        >
                            <FacetPopover
                                label="Kind"
                                options={["Feature", "Vocabulary"]}
                                value={kindFilter}
                                onChange={setKindFilter}
                            />
                        </Flex>
                    )}
                    {axis === "work" && board.fallback && (
                        <Callout.Root
                            className="fallback-banner"
                            color="amber"
                            role="status"
                        >
                            <Callout.Text>
                                The board could not be read: {board.unavailable}
                                . Showing the item folders only.{" "}
                                <Button
                                    size="1"
                                    variant="soft"
                                    type="button"
                                    onClick={() => void reloadBoard()}
                                >
                                    Retry
                                </Button>
                            </Callout.Text>
                        </Callout.Root>
                    )}
                    {axis !== "work" && kept && (
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
                    )}
                    <div
                        className="list"
                        role="tree"
                        aria-label="Objects"
                        onKeyDown={handleTreeKeyboard}
                    >
                        {!kept ? (
                            <Text className="empty" color="gray">
                                This project keeps no{" "}
                                {axis === "work"
                                    ? "work"
                                    : LABELS[axis].toLowerCase()}
                                .
                            </Text>
                        ) : tree.nodes.length ? (
                            <Tree
                                nodes={tree.nodes}
                                axis={axis}
                                selected={selected}
                                expanded={effectiveExpanded}
                                visible={visible}
                                rowClass={
                                    axis === "work" ? workRowClass : undefined
                                }
                                people={people}
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
                    </div>
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
                                onClick={() => {
                                    void load()
                                    void reloadBoard()
                                }}
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
                            data={data}
                            onSave={() => void save()}
                            onCancel={cancelEditor}
                            onRefreshConflict={() => void refreshConflict()}
                        />
                    ) : loadingDetail && !workDetail && !detail ? (
                        <Text className="empty" color="gray">
                            Loading...
                        </Text>
                    ) : axis === "work" && workDetail && project ? (
                        <WorkPage
                            project={project}
                            detail={workDetail}
                            readFile={readFile}
                            onRetry={retryDetail}
                        />
                    ) : axis === "work" && detailError ? (
                        <Text className="empty" color="gray">
                            {detailError}
                        </Text>
                    ) : axis !== "work" && detail ? (
                        <DetailView
                            axis={axis}
                            detail={detail}
                            onEdit={enterCore}
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
