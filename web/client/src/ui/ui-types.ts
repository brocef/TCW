import type {
    Axis,
    CapabilityDetail,
    CapabilityItem,
    TaxonomyDetail,
    TaxonomyItem,
    WorkDetail,
    WorkItem,
} from "../model/types"

export type TClientData = {
    work: WorkItem[]
    taxonomy: TaxonomyItem[]
    capabilities: CapabilityItem[]
}

export type TDetail = WorkDetail | TaxonomyDetail | CapabilityDetail

export type TDraft = Record<string, unknown> & { body?: string }

export type TEditorSession =
    | { mode: "create"; axis: Axis; draft: TDraft }
    | {
          mode: "core"
          axis: Axis
          ref: string
          revision: string
          draft: TDraft
          original: TDraft
      }
    | {
          mode: "resource"
          axis: "work"
          kind: "artifacts" | "sidecars" | "plan-stages"
          slug: string
          name: string
          revision: string
          mediaType: string
          draft: string
          original: string
      }

export type TListPaneState = {
    axis: Axis
    selected: string | null
    filter: string
    expanded: Record<Axis, Set<string>>
}

export type TLifecycleAction = "start" | "complete" | "drop"
