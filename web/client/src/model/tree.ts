import type { TreeNode, WorkItem } from "./types"

export type TWorkSortKey = "name" | "created" | "priority"
export type TSortDirection = "ascending" | "descending"

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

/** The work tree by `parent`. Keys are full identifiers, which is what `parent`
 * holds; an item whose parent is not on the board (another project's item,
 * or one the filters left out of the load) is a root. A cycle is broken by
 * making its first unreachable member a root. */
export function buildWorkTree(items: WorkItem[]): Array<TreeNode<WorkItem>> {
    const index = new Map<string, TreeNode<WorkItem>>()
    for (const item of items) {
        const key = item["full-id"]
        if (!index.has(key)) {
            index.set(key, {
                name: item.title || key,
                path: key,
                item,
                children: [],
            })
        }
    }
    const roots: Array<TreeNode<WorkItem>> = []
    const parentOf = new Map<string, string>()
    for (const [key, node] of index) {
        const parentKey = node.item?.parent ?? ""
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

/** Sort a work tree: by stage, in the table's order (an item with no stage
 * after every stage), then by the chosen key. A missing priority sorts after
 * the lowest one, whichever the direction. */
export function sortWorkTree(
    nodes: Array<TreeNode<WorkItem>>,
    key: TWorkSortKey,
    direction: TSortDirection,
    stageOrder: string[],
    priorityOrder: string[]
): Array<TreeNode<WorkItem>> {
    const stageRank = (item: WorkItem | null) => {
        const index = stageOrder.indexOf(item?.stage ?? "")
        return index === -1 ? stageOrder.length : index
    }
    const compareValue = (left: WorkItem, right: WorkItem) => {
        if (key === "priority") {
            const rank = (item: WorkItem) => {
                const index = priorityOrder.indexOf(item.priority ?? "")
                return index === -1 ? priorityOrder.length : index
            }
            const leftRank = rank(left)
            const rightRank = rank(right)
            if (leftRank === rightRank) return 0
            if (leftRank === priorityOrder.length) return 1
            if (rightRank === priorityOrder.length) return -1
            const result = leftRank - rightRank
            return direction === "ascending" ? result : -result
        }
        const leftValue =
            key === "name" ? left.title || left["full-id"] : left.created
        const rightValue =
            key === "name" ? right.title || right["full-id"] : right.created
        if (key === "created" && (!leftValue || !rightValue)) {
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
        const byStage = stageRank(left.item) - stageRank(right.item)
        if (byStage) return byStage
        if (!left.item || !right.item)
            return left.name.localeCompare(right.name)
        return compareValue(left.item, right.item)
    }
    return [...nodes].sort(compareNodes).map((node) => ({
        ...node,
        children: sortWorkTree(
            node.children,
            key,
            direction,
            stageOrder,
            priorityOrder
        ),
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

/** The full identifiers of an item's ancestors on the board, outermost
 * first. */
export function workAncestors(slug: string, items: WorkItem[]): string[] {
    const bySlug = new Map(items.map((item) => [item["full-id"], item]))
    const chain: string[] = []
    const visited = new Set([slug])
    let cursor = slug
    while (cursor) {
        const parent = bySlug.get(cursor)?.parent
        if (!parent || visited.has(parent) || !bySlug.has(parent)) break
        chain.unshift(parent)
        visited.add(parent)
        cursor = parent
    }
    return chain
}
