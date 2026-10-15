import type {
    Axis,
    AxisItem,
    CapabilityItem,
    TaxonomyItem,
    WorkItem,
} from "../model/types"
import { folderOf } from "../model/work"

export const AXES: Axis[] = ["taxonomy", "capabilities", "work"]

export const LABELS: Record<Axis, string> = {
    work: "Work",
    taxonomy: "Taxonomy",
    capabilities: "Capabilities",
}

/** What a row is selected and routed by: a work item's folder, a term's or
 * capability's qualified reference. */
export function itemKey(axis: Axis, item: AxisItem): string {
    if (axis === "work") return folderOf((item as WorkItem).slug)
    if (axis === "taxonomy") {
        const term = item as TaxonomyItem
        return term.qualified ?? term.slug
    }
    const capability = item as CapabilityItem
    return capability.qualified ?? capability.path
}

export function itemTitle(axis: Axis, item: AxisItem): string {
    if (axis === "work")
        return (item as WorkItem).title || (item as WorkItem).slug
    if (axis === "taxonomy")
        return (item as TaxonomyItem).name ?? (item as TaxonomyItem).slug
    return (item as CapabilityItem).name ?? (item as CapabilityItem).path
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
