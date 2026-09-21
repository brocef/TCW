export type Axis = "work" | "taxonomy" | "capabilities"

// Canonical work statuses, mirroring WORK_STATUSES in tcw/store/base.py.
// Display precedence is a separate concern — see WORK_STATUS_ORDER in ./tree.
export const WORK_STATUSES = [
    "backlog",
    "active",
    "review",
    "completed",
    "discarded",
]

export type JsonRecord = Record<string, unknown>

/**
 * An item's tracker binding, as `tcw work show --json` carries it: what the
 * binding file records, never what the tracker says now. `null` when unbound
 * and nothing is owed.
 *
 * Four shapes, and only the first has a `ticket`. Narrow on the presence of
 * `ticket` rather than on the absence of the others: a reader that excluded the
 * shapes it knew about was what crashed the whole page when `owed` was added.
 */
export type TTrackerBinding =
    | {
          provider: string
          project: string
          part: string
          ticket: { id: string; key: string; url: string }
          bound: string
          /** What did not reach the tracker, while it has not. */
          sync:
              | null
              | {
                    state: "pending" | "conflicting"
                    move: string
                    since: string
                    reason: string
                    at: string
                }
              | { problem: string }
          /** A progress comment that did not post, while it has not. */
          comment:
              | null
              | {
                    move: string
                    event: string
                    state: "pending" | "conflicting"
                    reason: string
                    at: string
                }
              | { problem: string }
      }
    | { problem: string }
    /** A ticket that filing was to create and could not. Not a binding. */
    | { owed: { since: string; reason: string } }
    /** A ticket that was created and never bound. Also not a binding. */
    | { created: { key: string; id: string } }

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
    tracker?: TTrackerBinding | null
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
    /** Written by a command, not a person — readable, never editable here. */
    generated?: boolean
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
