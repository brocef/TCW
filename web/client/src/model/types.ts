export type Axis = "work" | "taxonomy" | "capabilities"

export type JsonRecord = Record<string, unknown>

/** What a part of an answer holds when the backend could not give it: the
 * exception's message. Only the part fails; the rest of the answer stands. */
export interface TUnavailable {
    unavailable: string
}

/** One row of the stage table, for an enabled stage, in table order. The
 * client holds no stage names: every stage it shows comes from these rows. */
export interface TStageRow {
    name: string
    kind: "flow" | "terminal" | "side"
    artifact: "document" | "rounds" | "none"
    verdict: boolean
    onReject: string | null
    /** Kept by the backend rather than in the item folder. */
    external: boolean
    completion: boolean
    discard: boolean
}

export interface TConnectedProject {
    id: string
    relation: string
    /** Declared, and found on this machine. */
    present: boolean
    /** Creating into it is refused, as the CLI decides; null when it is not
     * on this machine. */
    readOnly: boolean | null
}

export interface TProject {
    id: string
    /** Who owns an item's request, comments, stage and properties: the files
     * on disk ("local"), or the backend, when they are read-only here. */
    recordOwner: "local" | "backend"
    stages: TStageRow[]
    inboxStage: string
    startStage: string
    inboxItems: boolean
    /** The registered tags, or why they cannot be read: a parent that is not
     * on this machine, or one that passes them with a problem (TCW-109). */
    tags: string[] | TUnavailable
    scales: { priority: string[]; size: string[] }
    capabilityScales: {
        status: string[]
        priority: string[]
        lifecycle: string[]
    }
    /** Which of priority, effort and complexity a new item may set. */
    createFields: string[] | TUnavailable
    user: string | null
    people: Record<string, string>
    projects: TConnectedProject[]
    axes: Record<Axis, boolean>
}

/** An item record: what `tcw work list --json` and `show --json` carry. */
export interface WorkItem {
    /** `<project>.work/<folder>` (TCW-110 Design 4.3). */
    "full-id": string
    owner: string
    title: string
    stage: string | null
    created: string
    priority: string | null
    effort: string | null
    complexity: string | null
    tags: string[]
    assignee: string | null
    parent: string | null
    "blocked-by": string[]
    blocks: string[]
    children: string[]
    path: string
    /** Linked tickets that have no item. */
    untracked: string[]
    /** A board row the backend could not read: only its folder is known. */
    unread?: boolean
}

/** A board row when the backend cannot answer: the folder alone. */
export interface TFallbackRow {
    "full-id": string
    owner: string
    path: string
}

export interface TBoard {
    items: Array<WorkItem | TFallbackRow>
    people: Record<string, string>
    fallback: boolean
    unavailable?: string
}

export interface TComment {
    at: string
    author: string
    text: string
}

export interface TFileRef {
    path: string
    revision: string | null
}

export interface TDocumentRef extends TFileRef {
    present: boolean
}

export interface TRoundRef extends TFileRef {
    number: number
    verdict?: string
}

/** One stage's files, or the declaration file (`stage` null). */
export interface TStageFiles {
    stage: string | null
    artifact: "document" | "rounds" | "declaration"
    verdict?: boolean
    document?: TDocumentRef
    rounds?: TRoundRef[]
    handoffs?: TFileRef[]
}

export interface TVerdict {
    stage: string
    verdict: string
}

export interface TFinding {
    severity: string
    where: string
    message: string
}

export interface WorkDetail {
    folder: string
    item: WorkItem | TUnavailable
    /** Present only when the backend keeps the request. */
    requestText?: string | null | TUnavailable
    comments: TComment[] | TUnavailable
    commentsLimited: boolean
    people: Record<string, string>
    link: { label: string; url: string } | null
    files: TStageFiles[]
    verdicts: TVerdict[]
    /** Items skipped as unreadable while computing blocks and children. */
    warnings: string[]
}

export interface TFileContent {
    content: string
    revision: string
}

export interface TDeclarationLists {
    new: string[]
    changed: string[]
    removed: string[]
}

export interface TDeclaration {
    revision: string | null
    present: boolean
    /** The parser's message, when the file cannot be read as lists. */
    problem: string | null
    content?: string
    capabilities?: TDeclarationLists
    taxonomy?: TDeclarationLists
}

export interface TTicket {
    key: string
    summary: string | null
    status: string | null
    created: string | null
    reporter: string | null
    url: string
    description: string | null
}

export interface TaxonomyItem extends JsonRecord {
    /** `<project>.taxonomy/<slug>` (TCW-110 Design 4.5). */
    "full-id": string
    owner: string
    name?: string
    kind?: string
    parent?: string
    relates_to?: string[]
    vocabulary?: string[]
    description?: string
    modified?: string
}

export interface CapabilityItem extends JsonRecord {
    /** `<project>.capabilities/<path>` (TCW-110 Design 4.5). */
    "full-id": string
    owner: string
    name?: string
    status?: string
    fields?: Record<string, string | string[]>
    body?: string
    modified?: string
}

export type AxisItem = WorkItem | TaxonomyItem | CapabilityItem

export interface TaxonomyDetail {
    term: TaxonomyItem
    coreRevision: string
}

export interface CapabilityDetail {
    capability: CapabilityItem
    coreRevision: string
}

export interface ApiResult<T = JsonRecord> {
    ok: boolean
    status: number
    data: T | null
    error: string
    code?: string
}

export interface TreeNode<T> {
    name: string
    path: string
    item: T | null
    children: Array<TreeNode<T>>
}
