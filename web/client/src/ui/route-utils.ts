import type {
    Axis,
    AxisItem,
    CapabilityItem,
    TaxonomyItem,
    WorkItem,
} from "../model/types"
import { parseFullId, routeKey } from "../model/identifier"
import { buildPathTree } from "../model/tree"
import type { TreeNode } from "../model/types"

export const AXES: Axis[] = ["taxonomy", "capabilities", "work"]

export const LABELS: Record<Axis, string> = {
    work: "Work",
    taxonomy: "Taxonomy",
    capabilities: "Capabilities",
}

/** What a row is selected and routed by: the id-path of an object this
 * project owns (a work item's folder), and the whole full identifier of
 * any other project's, in every namespace (TCW-113 Design 6.3). */
export function itemKey(axis: Axis, item: AxisItem, projectId: string): string {
    return routeKey(
        (item as WorkItem | TaxonomyItem | CapabilityItem)["full-id"],
        projectId
    )
}

/** The key of the record a term or capability names as its `parent`, in
 * the form `itemKey` gives, or null when it names none or its `parent` is
 * not a full identifier. The trees nest a record under this key. */
export function parentItemKey(
    item: TaxonomyItem | CapabilityItem,
    projectId: string
): string | null {
    const parent = item.parent
    if (!parent || !parseFullId(parent)) return null
    return routeKey(parent, projectId)
}

/** The taxonomy or capabilities tree: each record under its folder, or
 * under the record its `parent` names. */
export function buildRecordTree(
    axis: Axis,
    items: AxisItem[],
    projectId: string
): Array<TreeNode<AxisItem>> {
    return buildPathTree(
        items,
        (item) => itemKey(axis, item, projectId),
        (item) =>
            parentItemKey(item as TaxonomyItem | CapabilityItem, projectId)
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
