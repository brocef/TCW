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
    isUnavailable,
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
import { ScopeControl } from "./scope-control"
import { scopeParams, scopeSearch, withScope } from "../model/scope"
import { RefusalContext, useRefusals } from "./refusals"
import { beginResize, loadExpanded } from "./ui-state"
import { ProjectIdContext } from "./project-context"
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
    CapabilityList,
    JsonRecord,
    TBoard,
    TFileContent,
    TProject,
    TScopeProject,
    TaxonomyDetail,
    TaxonomyItem,
    TaxonomyList,
    TreeNode,
    WorkDetail,
    WorkItem,
} from "../model/types"
import { WorkPage } from "./work-views"
import { LinkContext } from "./link-context"
import { tcwLinkOptions } from "../model/reference-search"
import { fullIdText, parseFullId } from "../model/identifier"
import {
    CommentBox,
    FileEditor,
    NewItemForm,
    PropertiesForm,
    TicketsView,
    type TFileSession,
} from "./work-forms"
import { DeclarationSection } from "./declaration-form"
import type { TNewFileKind } from "./work-document-tabs"

/** What the work detail pane shows in place of the item page. */
type TWorkMode =
    | null
    | { mode: "file"; session: TFileSession }
    | { mode: "properties" }
    | { mode: "new" }
    | { mode: "tickets" }

type TBoardState = {
    people: Record<string, string>
    fallback: boolean
    unavailable?: string
    projects?: TScopeProject[]
}

export function App() {
    const location = useLocation()
    const navigate = useNavigate()
    const initialRoute = useRef(parsePath(location.pathname)).current
    // The scope and the project the page covers, kept in the URL's query
    // string on every path (TCW-113 Design 6.6, plan choice 14).
    const scopeKey = scopeSearch(scopeParams(location.search))
    const scopeChoice = useMemo(() => scopeParams(scopeKey), [scopeKey])
    const [axis, setAxis] = useState<Axis>(initialRoute.axis)
    const [selected, setSelected] = useState<string | null>(initialRoute.key)
    const [project, setProject] = useState<TProject | null>(null)
    const projectId = project?.id ?? ""
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
    // What holds unsaved work: "form" for the open editor or form, and a
    // part of the item page each (the declaration, blocks, a comment), so
    // one part saving does not forget another.
    const [dirtyParts, setDirtyParts] = useState<ReadonlySet<string>>(
        () => new Set()
    )
    const dirty = dirtyParts.size > 0
    const markDirty = useCallback((part: string, value: boolean) => {
        setDirtyParts((old) => {
            if (old.has(part) === value) return old
            const next = new Set(old)
            if (value) next.add(part)
            else next.delete(part)
            return next
        })
    }, [])
    /** true: the open editor or form has unsaved work; false: nothing on
     * the page has any (it was saved, discarded, or left). */
    const setDirty = useCallback(
        (value: boolean) => {
            if (value) markDirty("form", true)
            else setDirtyParts((old) => (old.size ? new Set() : old))
        },
        [markDirty]
    )
    const declarationDirty = useCallback(
        (value: boolean) => markDirty("declaration", value),
        [markDirty]
    )
    const commentDirty = useCallback(
        (value: boolean) => markDirty("comment", value),
        [markDirty]
    )
    const editorRefusals = useRefusals()
    const [saving, setSaving] = useState(false)
    const [errors, setErrors] = useState<string[]>([])
    const [conflict, setConflict] = useState<unknown>(null)
    const [warnings, setWarnings] = useState<string[]>([])
    const [toast, setToast] = useState("")
    // A problem after an action that otherwise succeeded, shown until the
    // page moves on: a ticket adopted whose post hook failed.
    const [problem, setProblem] = useState("")
    const [workMode, setWorkMode] = useState<TWorkMode>(null)
    // Every item, whatever the board's filters, for the fields that suggest
    // items and for `tcw://` links. Read only while something offers them.
    const [allWork, setAllWork] = useState<WorkItem[] | null>(null)
    // The taxonomy and capabilities a reference may name: the served
    // project's view, apart from the lists shown (plan choice 15).
    // Each list's `projects`, under a scope other than `own`, for the
    // notices of unavailable projects (Design 6.8).
    const [listProjects, setListProjects] = useState<{
        taxonomy?: TScopeProject[]
        capabilities?: TScopeProject[]
    }>({})
    const [pickable, setPickable] = useState<{
        taxonomy: TaxonomyItem[]
        capabilities: CapabilityItem[]
    }>({ taxonomy: [], capabilities: [] })
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

    const loadBoard = useCallback(
        async (search: string) => {
            const found = await fetchJson<TBoard>(
                withScope(`/api/work${search}`, scopeChoice)
            )
            setData((old) => ({ ...old, work: boardRows(found) }))
            setBoard({
                people: found.people,
                fallback: found.fallback,
                unavailable: found.unavailable,
                projects: found.projects,
            })
        },
        [scopeChoice]
    )

    const loadRecords = useCallback(
        async (found: TProject) => {
            // The lists shown, and apart from them what the pickers offer: the
            // served project's view, `scope=up`, whatever the lists show
            // (TCW-113 Design 6.6, plan choice 15).
            const none: TaxonomyList & CapabilityList = {
                terms: [],
                capabilities: [],
            }
            const [taxonomy, capabilities, taxonomyUp, capabilitiesUp] =
                await Promise.all([
                    found.axes.taxonomy
                        ? fetchJson<TaxonomyList>(
                              withScope("/api/taxonomy", scopeChoice)
                          )
                        : Promise.resolve(none),
                    found.axes.capabilities
                        ? fetchJson<CapabilityList>(
                              withScope("/api/capabilities", scopeChoice)
                          )
                        : Promise.resolve(none),
                    found.axes.taxonomy
                        ? fetchJson<TaxonomyList>("/api/taxonomy?scope=up")
                        : Promise.resolve(none),
                    found.axes.capabilities
                        ? fetchJson<CapabilityList>(
                              "/api/capabilities?scope=up"
                          )
                        : Promise.resolve(none),
                ])
            setData((old) => ({
                ...old,
                taxonomy: taxonomy.terms,
                capabilities: capabilities.capabilities,
            }))
            setListProjects({
                taxonomy: taxonomy.projects,
                capabilities: capabilities.projects,
            })
            setPickable({
                taxonomy: taxonomyUp.terms,
                capabilities: capabilitiesUp.capabilities,
            })
        },
        [scopeChoice]
    )

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
                navigate(pathFor(axis, selected) + scopeKey, { replace: true })
                return
            }
            setProblem("")
            setEditor(null)
            setWorkMode(null)
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
        // The scope decides its `children` and `blocks` (Design 3.3).
        void fetchJson<WorkDetail>(
            withScope(`/api/work/${encodeRef(selected)}`, scopeChoice)
        )
            .then((found) => {
                if (stale) return
                setWorkDetail(found)
                // The key the page is kept at: the folder of this project's
                // item, the full identifier of another's (Design 6.3).
                const owner = parseFullId(selected)?.project ?? projectId
                const key =
                    owner === projectId
                        ? found.folder
                        : fullIdText(owner, "work", found.folder)
                if (key !== selected) {
                    setSelected(key)
                    navigate(pathFor("work", key) + scopeKey, {
                        replace: true,
                    })
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
    }, [axis, selected, detailVersion, scopeChoice]) // eslint-disable-line react-hooks/exhaustive-deps

    useEffect(() => {
        if (
            axis === "work" ||
            !selected ||
            !(data[axis] as AxisItem[]).some(
                (item) => itemKey(axis, item, projectId) === selected
            )
        ) {
            setDetail(null)
            return
        }
        setLoadingDetail(true)
        void fetchJson<Detail>(
            withScope(`/api/${axis}/${encodeRef(selected)}`, scopeChoice)
        )
            .then(setDetail)
            .catch((error) => setLoadError(String(error)))
            .finally(() => setLoadingDetail(false))
    }, [axis, selected, data, projectId, scopeChoice])

    // Only views that offer items to choose read every item: the forms
    // and editors, and an item page whose record is edited here. The
    // tickets view offers none.
    const wantsAll = Boolean(
        axis === "work" &&
        project?.axes.work &&
        (workMode !== null
            ? workMode.mode !== "tickets"
            : workDetail !== null && project.recordOwner === "local")
    )
    useEffect(() => {
        if (!wantsAll || allWork !== null) return
        let stale = false
        fetchJson<TBoard>("/api/work?all=1")
            .then((found) => {
                if (!stale) setAllWork(boardRows(found))
            })
            .catch(() => {
                // The board's rows of the served project alone: under a
                // scope the board holds other projects' items too.
                if (!stale)
                    setAllWork(
                        data.work.filter((item) => item.owner === projectId)
                    )
            })
        return () => {
            stale = true
        }
    }, [wantsAll, allWork]) // eslint-disable-line react-hooks/exhaustive-deps
    const links = useMemo(
        () =>
            tcwLinkOptions({
                projectId,
                work: allWork ?? data.work,
                ...pickable,
            }),
        [allWork, data, pickable, projectId]
    )

    const readFile = useCallback(
        (path: string) =>
            fetchJson<TFileContent>(
                `/api/work/${encodeRef(selected ?? "")}/files/${encodePath(path)}`
            ),
        [selected]
    )

    // The stage of the file last opened in the editor, so that the item's
    // page comes back on that stage's tab rather than on the item's own.
    const [fileStage, setFileStage] = useState<{
        folder: string
        stage: string
    } | null>(null)

    // False when the user chose to stay on a page with unsaved changes.
    // `saved` is for a form that has just saved its work: the `dirty` this
    // render holds is still the form's, so asking would offer to discard
    // what is already saved.
    const navigateTo = (
        nextAxis: Axis,
        key: string | null,
        saved = false
    ): boolean => {
        if (!saved && !confirmLeave()) return false
        setFileStage(null)
        setProblem("")
        setEditor(null)
        setWorkMode(null)
        setDirty(false)
        setErrors([])
        setConflict(null)
        setDetail(null)
        setWorkDetail(null)
        setAxis(nextAxis)
        setSelected(key)
        navigate(pathFor(nextAxis, key) + scopeKey)
        if (key) {
            const ancestors =
                nextAxis === "work"
                    ? workAncestors(
                          data.work.find(
                              (item) => itemKey("work", item, projectId) === key
                          )?.["full-id"] ?? "",
                          data.work
                      )
                    : pathAncestors(key)
            setExpanded((old) => ({
                ...old,
                [nextAxis]: new Set([...old[nextAxis], ...ancestors]),
            }))
        }
        return true
    }

    // Leaving the page is asked about once, by navigateTo; staying keeps
    // both the unsaved work and the filter as they were.
    const updateFilter = (value: string) => {
        if (navigateTo(axis, null)) setFilter(value)
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
                : buildPathTree(currentItems, (item) =>
                      itemKey(axis, item, projectId)
                  )
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
        projectId,
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
        let bodyNote = false
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
            ref = itemKey("taxonomy", term, projectId)
            revision = payload.coreRevision
        } else {
            const payload = detail as CapabilityDetail
            const capability = payload.capability
            // The declared description, not the combined body, which also
            // holds attached documents or an inherited description: sending
            // that back would write them into this one (TCW-112 Design 4.5).
            const declared = payload.declaredDescription ?? ""
            draft = {
                ...(capability.fields ?? {}),
                body: declared,
            }
            bodyNote = (capability.body ?? "") !== declared
            ref = itemKey("capabilities", capability, projectId)
            revision = payload.coreRevision
        }
        setEditor({
            mode: "core",
            axis,
            ref,
            revision,
            draft,
            original: structuredClone(draft),
            bodyNote,
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
        if (editorRefusals.pending.length) {
            setErrors(editorRefusals.pending)
            return
        }
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
                        // Only a Feature has a vocabulary.
                        vocabulary:
                            draft.kind === "Feature"
                                ? draft.vocabulary
                                : undefined,
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
    const references = {
        projectId,
        ...data,
        ...pickable,
        work: allWork ?? data.work,
        people,
        user: project?.user ?? null,
    }
    // In filesystem mode the item record is the files' own and editable;
    // when the backend owns it, only the stage files are edited here.
    // Another project's item is read here and changed nowhere (TCW-113
    // Design 6.7): its owner is the project its key names.
    const ownsItem =
        (parseFullId(selected ?? "")?.project ?? projectId) === projectId
    const ownsRecord = project?.recordOwner === "local" && ownsItem

    const leaveWorkMode = () => {
        if (!confirmLeave()) return
        setWorkMode(null)
        setDirty(false)
    }
    const workSaved = (message: string, response: unknown) => {
        showSaveResult(message, response)
        // A form that replaced the page is done; a part of the page (the
        // declaration, blocks, a comment) clears its own unsaved state, and
        // the other parts keep theirs.
        if (workMode !== null) setDirty(false)
        setWorkMode(null)
        // Something was saved, so the full list may have changed.
        setAllWork(null)
        retryDetail()
        void reloadBoard()
    }
    /** Replace the item page with a form, after asking when anything on
     * the page is unsaved, since the page's drafts go with it. */
    const enterWorkMode = (mode: TWorkMode, asked = false) => {
        if (!asked && !confirmLeave()) return false
        setWorkMode(mode)
        setDirty(false)
        setWarnings([])
        setProblem("")
        return true
    }
    const openFile = async (stage: string, path: string) => {
        if (!selected || !confirmLeave()) return
        try {
            const found = await readFile(path)
            const row = stages.find((candidate) => candidate.name === stage)
            // Asked above, before the read.
            enterWorkMode(
                {
                    mode: "file",
                    session: {
                        folder: selected,
                        stage,
                        path,
                        revision: found.revision,
                        content: found.content,
                        verdict:
                            Boolean(row?.verdict) &&
                            /\/round-\d+\.md$/.test(path),
                    },
                },
                true
            )
            setFileStage({ folder: selected, stage })
        } catch (error) {
            showToast(
                `Could not open ${path}: ${error instanceof Error ? error.message : String(error)}`
            )
        }
    }
    const newFile = async (stage: string, kind: TNewFileKind) => {
        if (!selected || !confirmLeave()) return
        const result = await requestJson<{ path: string; template: string }>(
            `/api/work/${encodeRef(selected)}/files`,
            "POST",
            { stage, kind }
        )
        if (!result.ok || !result.data) {
            showToast(result.error || `Could not start a new ${kind}`)
            return
        }
        const row = stages.find((candidate) => candidate.name === stage)
        // Asked above, before the request.
        enterWorkMode(
            {
                mode: "file",
                session: {
                    folder: selected,
                    stage,
                    path: result.data.path,
                    revision: null,
                    content: result.data.template,
                    verdict: kind === "round" && Boolean(row?.verdict),
                },
            },
            true
        )
        setFileStage({ folder: selected, stage })
    }
    const openNewItem = () => {
        enterWorkMode({ mode: "new" })
    }

    return (
        <ProjectIdContext.Provider value={projectId}>
            <LinkContext.Provider value={links}>
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
                        {project && (
                            <ScopeControl
                                scopes={project.scopes}
                                choice={scopeChoice}
                                onChange={(next) => {
                                    if (!confirmLeave()) return
                                    setDirty(false)
                                    setEditor(null)
                                    setWorkMode(null)
                                    navigate(
                                        location.pathname + scopeSearch(next)
                                    )
                                }}
                            />
                        )}
                        <SettingsControl />
                    </nav>
                </header>
                <main
                    className="shell"
                    style={
                        {
                            "--list-width": `${listWidth * 100}%`,
                        } as CSSProperties
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
                                    options={
                                        isUnavailable(project.tags)
                                            ? []
                                            : project.tags
                                    }
                                    unavailable={
                                        isUnavailable(project.tags)
                                            ? project.tags.unavailable
                                            : undefined
                                    }
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
                        {(axis === "work" ? board.projects : listProjects[axis])
                            ?.filter((entry) => entry.unavailable)
                            .map((entry) => (
                                <Callout.Root
                                    className="unavailable-project"
                                    color="amber"
                                    role="status"
                                    key={entry.id}
                                >
                                    <Callout.Text>
                                        Project {entry.id} could not be read, so
                                        its objects are not listed:{" "}
                                        {entry.unavailable}
                                    </Callout.Text>
                                </Callout.Root>
                            ))}
                        {axis === "work" && board.fallback && (
                            <Callout.Root
                                className="fallback-banner"
                                color="amber"
                                role="status"
                            >
                                <Callout.Text>
                                    The board could not be read:{" "}
                                    {board.unavailable}. Showing the item
                                    folders only.{" "}
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
                        {axis === "work" && kept && project && (
                            <Flex className="create-row" gap="2">
                                <Button
                                    className="create-btn"
                                    variant="outline"
                                    type="button"
                                    onClick={openNewItem}
                                >
                                    + New item
                                </Button>
                                {project.recordOwner === "backend" && (
                                    <Button
                                        variant="outline"
                                        type="button"
                                        onClick={() =>
                                            enterWorkMode({ mode: "tickets" })
                                        }
                                    >
                                        Tickets
                                    </Button>
                                )}
                            </Flex>
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
                                        axis === "work"
                                            ? workRowClass
                                            : undefined
                                    }
                                    people={people}
                                    onSelect={(key) => navigateTo(axis, key)}
                                    onToggle={(path) => {
                                        if (filter) return
                                        setExpanded((old) => {
                                            const next = new Set(old[axis])
                                            if (next.has(path))
                                                next.delete(path)
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
                        {problem && (
                            <Callout.Root color="red" role="alert">
                                <Callout.Text>{problem}</Callout.Text>
                            </Callout.Root>
                        )}
                        {warnings.length > 0 && (
                            <Callout.Root color="amber" role="alert">
                                <Callout.Text>
                                    <strong>
                                        Saved with validation issues
                                    </strong>
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
                            <RefusalContext.Provider
                                value={editorRefusals.report}
                            >
                                <EditorView
                                    editor={editor}
                                    scales={
                                        project?.capabilityScales ?? {
                                            status: [],
                                            priority: [],
                                            lifecycle: [],
                                        }
                                    }
                                    setDraft={setDraft}
                                    saving={saving}
                                    errors={errors}
                                    conflict={conflict}
                                    data={{
                                        ...data,
                                        ...pickable,
                                        work: references.work,
                                    }}
                                    onSave={() => void save()}
                                    onCancel={cancelEditor}
                                    onRefreshConflict={() =>
                                        void refreshConflict()
                                    }
                                />
                            </RefusalContext.Provider>
                        ) : loadingDetail && !workDetail && !detail ? (
                            <Text className="empty" color="gray">
                                Loading...
                            </Text>
                        ) : axis === "work" &&
                          project &&
                          workMode?.mode === "new" ? (
                            <NewItemForm
                                project={project}
                                references={references}
                                onCreated={(folder, message) => {
                                    showToast(message)
                                    setWorkMode(null)
                                    setDirty(false)
                                    setAllWork(null)
                                    void reloadBoard()
                                    if (folder) navigateTo("work", folder, true)
                                }}
                                onCancel={leaveWorkMode}
                                onDirty={setDirty}
                            />
                        ) : axis === "work" && workMode?.mode === "tickets" ? (
                            <TicketsView
                                onAdopted={(folder, message, failed) => {
                                    showToast(message)
                                    setWorkMode(null)
                                    setAllWork(null)
                                    void reloadBoard()
                                    navigateTo("work", folder)
                                    // After navigating, which clears it: the
                                    // item is made, but say what failed.
                                    if (failed) setProblem(failed)
                                }}
                            />
                        ) : axis === "work" && workMode?.mode === "file" ? (
                            <FileEditor
                                session={workMode.session}
                                onSaved={workSaved}
                                onCancel={leaveWorkMode}
                                onDirty={setDirty}
                            />
                        ) : axis === "work" &&
                          project &&
                          workDetail &&
                          workMode?.mode === "properties" &&
                          !isUnavailable(workDetail.item) ? (
                            <PropertiesForm
                                project={project}
                                item={workDetail.item}
                                folder={workDetail.folder}
                                references={references}
                                onSaved={workSaved}
                                onCancel={leaveWorkMode}
                                onDirty={setDirty}
                                onReload={() => {
                                    setWorkMode(null)
                                    setDirty(false)
                                    retryDetail()
                                }}
                            />
                        ) : axis === "work" && workDetail && project ? (
                            <WorkPage
                                project={project}
                                detail={workDetail}
                                readFile={readFile}
                                onRetry={retryDetail}
                                editing={{
                                    openStage:
                                        fileStage?.folder === workDetail.folder
                                            ? fileStage.stage
                                            : undefined,
                                    onEditFile: ownsItem
                                        ? (stage, path) =>
                                              void openFile(stage, path)
                                        : undefined,
                                    onNewFile: ownsItem
                                        ? (stage, kind) =>
                                              void newFile(stage, kind)
                                        : undefined,
                                    onEditProperties: ownsRecord
                                        ? () => {
                                              enterWorkMode({
                                                  mode: "properties",
                                              })
                                          }
                                        : undefined,
                                    commentBox: ownsRecord ? (
                                        <CommentBox
                                            folder={workDetail.folder}
                                            onSaved={workSaved}
                                            onDirty={commentDirty}
                                        />
                                    ) : undefined,
                                    declaration: (
                                        <DeclarationSection
                                            folder={
                                                ownsItem
                                                    ? workDetail.folder
                                                    : (selected ?? "")
                                            }
                                            references={references}
                                            editable={ownsItem}
                                            onSaved={workSaved}
                                            onDirty={declarationDirty}
                                        />
                                    ),
                                }}
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
            </LinkContext.Provider>
        </ProjectIdContext.Provider>
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
