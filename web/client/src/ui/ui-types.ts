import type {
    Axis,
    CapabilityDetail,
    CapabilityItem,
    TaxonomyDetail,
    TaxonomyItem,
    WorkItem,
} from "../model/types"

export type TClientData = {
    work: WorkItem[]
    taxonomy: TaxonomyItem[]
    capabilities: CapabilityItem[]
}

/** A taxonomy entry's or capability's detail. A work item's page is drawn by
 * `work-views.tsx` from its own answer. */
export type TDetail = TaxonomyDetail | CapabilityDetail

export type TDraft = Record<string, unknown> & { body?: string }

/** The taxonomy and capability editor. */
export type TEditorSession =
    | { mode: "create"; axis: Exclude<Axis, "work">; draft: TDraft }
    | {
          mode: "core"
          axis: Exclude<Axis, "work">
          ref: string
          revision: string
          draft: TDraft
          original: TDraft
      }
