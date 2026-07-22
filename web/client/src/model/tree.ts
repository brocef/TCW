import type { TreeNode, WorkItem } from "./types"

export type TWorkSortKey = "name" | "modified"
export type TSortDirection = "ascending" | "descending"

const WORK_STATUS_ORDER = new Map([
    ["active", 0],
    ["backlog", 1],
    ["completed", 2],
])

export function buildPathTree<T>(
    items: T[],
    keyOf: (item: T) => string
): Array<TreeNode<T>> {
    const map = new Map<string, TreeNode<T>>()
    const itemByKey = new Map<string, T>()
    for (const item of items)
        if (!itemByKey.has(keyOf(item))) itemByKey.set(keyOf(item), item)
    for (const key of itemByKey.keys()) {
        let cursor = ""
        for (const segment of key.split("/")) {
            cursor = cursor ? `${cursor}/${segment}` : segment
            if (!map.has(cursor))
                map.set(cursor, {
                    name: segment,
                    path: cursor,
                    item: null,
                    children: [],
                })
        }
        map.get(key)!.item = itemByKey.get(key)!
    }
    const roots: Array<TreeNode<T>> = []
    for (const [path, node] of map) {
        const parentPath = path.slice(0, path.lastIndexOf("/"))
        const parent = parentPath ? map.get(parentPath) : undefined
        if (parent) parent.children.push(node)
        else roots.push(node)
    }
    return roots
}

function resolveParentKey(
    childKey: string,
    parentRef: string,
    keys: Set<string>
): string {
    const slash = childKey.lastIndexOf("/")
    if (slash !== -1) {
        const namespaced = `${childKey.slice(0, slash + 1)}${parentRef}`
        if (keys.has(namespaced)) return namespaced
    }
    return parentRef
}

export function buildWorkTree(items: WorkItem[]): Array<TreeNode<WorkItem>> {
    const index = new Map<string, TreeNode<WorkItem>>()
    for (const item of items) {
        if (!index.has(item.slug)) {
            index.set(item.slug, {
                name: item.title ?? item.slug,
                path: item.slug,
                item,
                children: [],
            })
        }
    }
    const keys = new Set(index.keys())
    const roots: Array<TreeNode<WorkItem>> = []
    const parentOf = new Map<string, string>()
    for (const [key, node] of index) {
        const parentRef = node.item?.parent?.trim()
        const parentKey = parentRef
            ? resolveParentKey(key, parentRef, keys)
            : ""
        if (parentKey && parentKey !== key && index.has(parentKey)) {
            index.get(parentKey)!.children.push(node)
            parentOf.set(key, parentKey)
        } else roots.push(node)
    }
    const reachable = new Set<string>()
    const mark = (node: TreeNode<WorkItem>) => {
        if (reachable.has(node.path)) return
        reachable.add(node.path)
        node.children.forEach(mark)
    }
    roots.forEach(mark)
    for (const [key, node] of index) {
        if (reachable.has(key)) continue
        const parent = index.get(parentOf.get(key) ?? "")
        if (parent)
            parent.children = parent.children.filter((child) => child !== node)
        roots.push(node)
        mark(node)
    }
    return roots
}

export function sortWorkTree(
    nodes: Array<TreeNode<WorkItem>>,
    key: TWorkSortKey,
    direction: TSortDirection
): Array<TreeNode<WorkItem>> {
    const compareValue = (left: WorkItem, right: WorkItem) => {
        const leftValue =
            key === "name" ? (left.title ?? left.slug) : (left.modified ?? "")
        const rightValue =
            key === "name"
                ? (right.title ?? right.slug)
                : (right.modified ?? "")
        if (key === "modified" && (!leftValue || !rightValue)) {
            if (!leftValue && !rightValue) return 0
            return leftValue ? -1 : 1
        }
        const result = leftValue.localeCompare(rightValue, undefined, {
            numeric: true,
            sensitivity: "base",
        })
        return direction === "ascending" ? result : -result
    }
    const compareNodes = (
        left: TreeNode<WorkItem>,
        right: TreeNode<WorkItem>
    ) => {
        const leftStatus = WORK_STATUS_ORDER.get(left.item?.status ?? "") ?? 3
        const rightStatus = WORK_STATUS_ORDER.get(right.item?.status ?? "") ?? 3
        if (leftStatus !== rightStatus) return leftStatus - rightStatus
        if (!left.item || !right.item)
            return left.name.localeCompare(right.name)
        return compareValue(left.item, right.item)
    }
    return [...nodes].sort(compareNodes).map((node) => ({
        ...node,
        children: sortWorkTree(node.children, key, direction),
    }))
}

export function pruneTree<T>(
    nodes: Array<TreeNode<T>>,
    predicate: (item: T) => boolean
): { nodes: Array<TreeNode<T>>; forceExpand: Set<string> } {
    const forceExpand = new Set<string>()
    const visit = (node: TreeNode<T>): TreeNode<T> | null => {
        const children = node.children
            .map(visit)
            .filter((child): child is TreeNode<T> => child !== null)
        if (children.length) {
            forceExpand.add(node.path)
            return { ...node, children }
        }
        return node.item && predicate(node.item) ? { ...node, children } : null
    }
    return {
        nodes: nodes
            .map(visit)
            .filter((node): node is TreeNode<T> => node !== null),
        forceExpand,
    }
}

export function pathAncestors(key: string): string[] {
    const parts = key.split("/")
    return parts
        .slice(1)
        .map((_part, index) => parts.slice(0, index + 1).join("/"))
}

export function workAncestors(key: string, items: WorkItem[]): string[] {
    const byKey = new Map(items.map((item) => [item.slug, item]))
    const keys = new Set(byKey.keys())
    const chain: string[] = []
    const visited = new Set([key])
    let cursor = key
    while (cursor) {
        const parentRef = byKey.get(cursor)?.parent?.trim()
        if (!parentRef) break
        const parent = resolveParentKey(cursor, parentRef, keys)
        if (visited.has(parent)) break
        chain.unshift(parent)
        visited.add(parent)
        cursor = parent
    }
    return chain
}
