import type {
    Axis,
    AxisItem,
    CapabilityItem,
    TaxonomyItem,
    WorkItem,
} from "../model/types"

export const AXES: Axis[] = ["taxonomy", "capabilities", "work"]

export const LABELS: Record<Axis, string> = {
    work: "Work",
    taxonomy: "Taxonomy",
    capabilities: "Capabilities",
}

export function itemKey(axis: Axis, item: AxisItem): string {
    if (axis === "work") return (item as WorkItem).slug
    if (axis === "taxonomy") {
        const term = item as TaxonomyItem
        return term.qualified ?? term.slug
    }
    const capability = item as CapabilityItem
    return capability.qualified ?? capability.path
}

export function itemTitle(axis: Axis, item: AxisItem): string {
    if (axis === "work")
        return (item as WorkItem).title ?? (item as WorkItem).slug
    if (axis === "taxonomy")
        return (item as TaxonomyItem).name ?? (item as TaxonomyItem).slug
    return (item as CapabilityItem).name ?? (item as CapabilityItem).path
}

export function pathFor(axis: Axis, key: string | null): string {
    if (!key) return `/${axis}`
    if (axis === "work") {
        const parts = key.split("/")
        const slug = parts.pop()!
        return `/${[...parts, "work", slug].map(encodeURIComponent).join("/")}`
    }
    return `/${[axis, ...key.split("/")].map(encodeURIComponent).join("/")}`
}

export function parsePath(pathname: string): {
    axis: Axis
    key: string | null
} {
    const segments = pathname.split("/").filter(Boolean).map(decodeURIComponent)
    const axisIndex = segments.findIndex((segment) =>
        AXES.includes(segment as Axis)
    )
    if (axisIndex === -1) return { axis: "work", key: null }
    const axis = segments[axisIndex] as Axis
    const rest = [
        ...segments.slice(0, axisIndex),
        ...segments.slice(axisIndex + 1),
    ]
    return { axis, key: rest.length ? rest.join("/") : null }
}
