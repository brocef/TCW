export type Axis = "work" | "taxonomy" | "capabilities"

export type JsonRecord = Record<string, unknown>

export interface WorkItem extends JsonRecord {
    slug: string
    title?: string
    status?: string
    modified?: string
    priority?: number | null
    effort?: string
    complexity?: string
    tags?: string[]
    parent?: string
    initiative?: string
    type?: string
    resolution?: string
    blocked_by?: Array<{ slug?: string; external?: string }>
    body?: string
}

export interface TMutationResponse extends JsonRecord {
    warnings?: string[]
}

export interface TaxonomyItem extends JsonRecord {
    slug: string
    qualified?: string
    name?: string
    kind?: string
    origin?: string
    parent?: string
    relates_to?: string[]
    vocabulary?: string[]
    description?: string
    modified?: string
}

export interface CapabilityItem extends JsonRecord {
    path: string
    qualified?: string
    name?: string
    status?: string
    origin?: string
    fields?: Record<string, string | string[]>
    body?: string
    modified?: string
}

export type AxisItem = WorkItem | TaxonomyItem | CapabilityItem

export interface ResourceSummary {
    name: string
    present: boolean
    revision?: string
    mediaType?: string
}

export interface TPlanStage extends ResourceSummary {
    id: string
    title: string
    depends_on: string[]
    effort?: string
    complexity?: string
    priority?: number | null
    tags: string[]
}

export interface WorkDetail {
    item: WorkItem
    coreRevision: string
    artifacts: ResourceSummary[]
    planStages: TPlanStage[]
    sidecars: ResourceSummary[]
    dodChecklist?: string[]
}

export interface TaxonomyDetail {
    term: TaxonomyItem
    coreRevision: string
}

export interface CapabilityDetail {
    capability: CapabilityItem
    coreRevision: string
}

export interface ResourceDetail {
    name: string
    content: string
    revision: string
    mediaType?: string
}

export interface ApiResult<T = JsonRecord> {
    ok: boolean
    status: number
    data: T | null
    error: string
}

export interface TreeNode<T> {
    name: string
    path: string
    item: T | null
    children: Array<TreeNode<T>>
}
