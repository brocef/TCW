import type {
    Axis,
    AxisItem,
    CapabilityItem,
    TaxonomyItem,
    WorkItem,
} from "../model/types"
import { parseFullId, routeKey } from "../model/identifier"
import { folderOf } from "../model/work"

export const AXES: Axis[] = ["taxonomy", "capabilities", "work"]

export const LABELS: Record<Axis, string> = {
    work: "Work",
    taxonomy: "Taxonomy",
    capabilities: "Capabilities",
}

/** What a row is selected and routed by: a work item's folder; a term's or
 * capability's id-path when this project owns it, and its whole full
 * identifier when it is inherited (TCW-110 Design 4.5). */
export function itemKey(axis: Axis, item: AxisItem, projectId: string): string {
    if (axis === "work") return folderOf((item as WorkItem)["full-id"])
    return routeKey(
        (item as TaxonomyItem | CapabilityItem)["full-id"],
        projectId
    )
}

/** The id-path of a term's or capability's full identifier. */
export function idPathOf(item: TaxonomyItem | CapabilityItem): string {
    return parseFullId(item["full-id"])?.idPath ?? item["full-id"]
}

/** Whether a term or capability is another project's. */
export function inherited(
    item: TaxonomyItem | CapabilityItem,
    projectId: string
): boolean {
    return item.owner !== projectId
}

export function itemTitle(axis: Axis, item: AxisItem): string {
    if (axis === "work")
        return (item as WorkItem).title || (item as WorkItem)["full-id"]
    const entry = item as TaxonomyItem | CapabilityItem
    return entry.name ?? idPathOf(entry)
}

/** `/work/<folder>`, `/taxonomy/<ref>`, `/capabilities/<path>`. */
export function pathFor(axis: Axis, key: string | null): string {
    if (!key) return `/${axis}`
    return `/${[axis, ...key.split("/")].map(encodeURIComponent).join("/")}`
}

export function parsePath(pathname: string): {
    axis: Axis
    key: string | null
} {
    const segments = pathname.split("/").filter(Boolean).map(decodeURIComponent)
    const axis = segments[0] as Axis
    if (!AXES.includes(axis)) return { axis: "work", key: null }
    const rest = segments.slice(1)
    return { axis, key: rest.length ? rest.join("/") : null }
}
