import { parseFullId } from "./identifier"
import type { CapabilityItem, TaxonomyItem, WorkItem } from "./types"
import { folderOf } from "./work"

export type TReferenceField =
    | "work-parent"
    | "work-assignee"
    | "work-blockers"
    | "taxonomy-parent"
    | "taxonomy-relates"
    | "taxonomy-vocabulary"
    | "capability-feature"
    | "capability-subject"
    | "capability-roles"
    | "capability-when"
    | "capability-blocked-by"
    | "capability-superseded-by"
    | "declaration-capabilities-new"
    | "declaration-capabilities-existing"
    | "declaration-taxonomy-new"
    | "declaration-taxonomy-existing"

export interface TReferenceOption {
    identifier: string
    displayName: string
}

export interface TRankedReferenceOption extends TReferenceOption {
    score: number
}

export interface THighlightPart {
    text: string
    matched: boolean
}

export interface TReferenceContext {
    work: WorkItem[]
    taxonomy: TaxonomyItem[]
    capabilities: CapabilityItem[]
    currentIdentifier?: string
    selected?: string[]
    /** Display names for people, when the backend gave them. */
    people?: Record<string, string>
    /** The current user, offered as an assignee. */
    user?: string | null
}

const RESULT_LIMIT = 10

function option(
    identifier: string,
    displayName: string | undefined
): TReferenceOption {
    return { identifier, displayName: displayName || identifier }
}

function descendantsOf(identifier: string, items: WorkItem[]): Set<string> {
    const descendants = new Set<string>()
    let changed = true
    while (changed) {
        changed = false
        for (const item of items) {
            if (
                item.parent &&
                (item.parent === identifier || descendants.has(item.parent)) &&
                !descendants.has(item["full-id"])
            ) {
                descendants.add(item["full-id"])
                changed = true
            }
        }
    }
    return descendants
}

/** Which suggestions a declaration list offers: a `new` entry may be a name
 * not yet in the ledger, `changed` and `removed` must name one that exists. */
export function declarationField(
    axis: "capabilities" | "taxonomy",
    list: "new" | "changed" | "removed"
): TReferenceField {
    return `declaration-${axis}-${list === "new" ? "new" : "existing"}`
}

export function referenceOptions(
    field: TReferenceField,
    context: TReferenceContext
): TReferenceOption[] {
    const current = context.currentIdentifier
    const selected = new Set(context.selected ?? [])
    const work = context.work.map((item) => option(item["full-id"], item.title))
    const taxonomy = context.taxonomy.map((item) =>
        option(item.qualified ?? item.slug, item.name)
    )
    const capabilities = context.capabilities.map((item) =>
        option(item.qualified ?? item.path, item.name)
    )
    if (field === "work-parent") {
        const excluded = current
            ? descendantsOf(current, context.work)
            : new Set<string>()
        if (current) excluded.add(current)
        return work.filter((item) => !excluded.has(item.identifier))
    }
    if (field.startsWith("declaration-"))
        return (
            field.startsWith("declaration-taxonomy") ? taxonomy : capabilities
        ).filter((item) => !selected.has(item.identifier))
    if (field === "work-assignee") {
        const people = context.people ?? {}
        const known = new Set<string>()
        for (const item of context.work)
            if (item.assignee) known.add(item.assignee)
        if (context.user) known.add(context.user)
        return [...known].map((id) =>
            option(
                id,
                `${people[id] ?? id}${id === context.user ? " (me)" : ""}`
            )
        )
    }
    if (field === "work-blockers")
        return work.filter(
            (item) =>
                item.identifier !== current && !selected.has(item.identifier)
        )
    if (field === "taxonomy-vocabulary")
        return context.taxonomy
            .filter((item) => item.kind === "Vocabulary")
            .map((item) => option(item.qualified ?? item.slug, item.name))
    if (field === "taxonomy-relates")
        return taxonomy.filter(
            (item) =>
                item.identifier !== current && !selected.has(item.identifier)
        )
    if (field === "taxonomy-parent") return taxonomy
    if (field === "capability-feature")
        return context.taxonomy
            .filter((item) => item.kind === "Feature")
            .map((item) => option(item.qualified ?? item.slug, item.name))
    if (field === "capability-subject")
        return context.taxonomy
            .filter((item) => item.kind === "Vocabulary")
            .map((item) => option(item.qualified ?? item.slug, item.name))
            .filter((item) => !selected.has(item.identifier))
    if (field === "capability-roles" || field === "capability-when") {
        // A role or condition is named by its path, `roles/…` or
        // `conditions/…`, inherited ones included: the ledger resolves the
        // bare path through `extends`.
        const prefix = field === "capability-roles" ? "roles/" : "conditions/"
        const seen = new Set<string>()
        return context.capabilities
            .filter((item) => item.path.startsWith(prefix))
            .map((item) => option(item.path, item.name))
            .filter((item) => {
                if (seen.has(item.identifier) || selected.has(item.identifier))
                    return false
                seen.add(item.identifier)
                return true
            })
    }
    return capabilities.filter(
        (item) => item.identifier !== current && !selected.has(item.identifier)
    )
}

export function rankReferenceOptions(
    options: TReferenceOption[],
    rawQuery: string
): TRankedReferenceOption[] {
    const query = rawQuery.trim().toLocaleLowerCase()
    if (!query) return []
    return options
        .flatMap((candidate) => {
            const name = candidate.displayName.toLocaleLowerCase()
            const identifier = candidate.identifier.toLocaleLowerCase()
            const nameScore = name.includes(query)
                ? query.length / name.length
                : 0
            const identifierScore = identifier.includes(query)
                ? query.length / identifier.length
                : 0
            if (!nameScore && !identifierScore) return []
            return [
                { ...candidate, score: (nameScore + identifierScore * 2) / 3 },
            ]
        })
        .sort(
            (left, right) =>
                right.score - left.score ||
                left.displayName.localeCompare(right.displayName) ||
                left.identifier.localeCompare(right.identifier)
        )
        .slice(0, RESULT_LIMIT)
}

export function highlightMatches(
    value: string,
    rawQuery: string
): THighlightPart[] {
    const query = rawQuery.trim()
    if (!query) return [{ text: value, matched: false }]
    const lowerValue = value.toLocaleLowerCase()
    const lowerQuery = query.toLocaleLowerCase()
    const parts: THighlightPart[] = []
    let cursor = 0
    while (cursor < value.length) {
        const index = lowerValue.indexOf(lowerQuery, cursor)
        if (index < 0) {
            parts.push({ text: value.slice(cursor), matched: false })
            break
        }
        if (index > cursor)
            parts.push({ text: value.slice(cursor, index), matched: false })
        parts.push({
            text: value.slice(index, index + query.length),
            matched: true,
        })
        cursor = index + query.length
    }
    return parts
}

/** Capability paths one segment at a time: under what is typed up to its
 * last `/`, the next segment of every existing path. A new segment is
 * allowed; these are only what exists. */
export function pathSegments(
    paths: string[],
    typed: string
): TReferenceOption[] {
    const prefix = typed.slice(0, typed.lastIndexOf("/") + 1)
    const found = new Map<string, TReferenceOption>()
    for (const path of paths) {
        if (!path.startsWith(prefix) || path.length === prefix.length) continue
        const segment = path.slice(prefix.length).split("/")[0]
        const identifier = `${prefix}${segment}`
        if (!found.has(identifier))
            found.set(identifier, { identifier, displayName: segment })
    }
    return [...found.values()]
}

/** Every object a `tcw://` link can name, in the three axes, inherited
 * entries included. A work item is named by its folder (`tcw://W/<folder>`),
 * never by a key a backend gives it, so a link reads the same in every
 * mode. */
export function tcwLinkOptions(context: TReferenceContext): TReferenceOption[] {
    return [
        ...context.work.map((item) =>
            option(`tcw://W/${folderOf(item["full-id"])}`, item.title)
        ),
        ...context.taxonomy.map((item) =>
            option(`tcw://T/${item.qualified ?? item.slug}`, item.name)
        ),
        ...context.capabilities.map((item) =>
            option(`tcw://C/${item.qualified ?? item.path}`, item.name)
        ),
    ]
}

/** The `tcw://` text being typed just before the caret, or null. */
export function typedLink(textBeforeCaret: string): string | null {
    const found = /tcw:\/\/[^\s()[\]<>"']*$/.exec(textBeforeCaret)
    return found ? found[0] : null
}

/** The warning a full identifier naming another project's item carries: it
 * is kept, but this page cannot check it. Null for anything else. */
export function otherProjectWarning(
    text: string,
    projectId: string
): string | null {
    const found = parseFullId(text.trim())
    if (!found || found.namespace !== "work" || found.project === projectId)
        return null
    return `${text.trim()} is in project ${found.project}, which this page does not check; make sure it exists`
}
