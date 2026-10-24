// Which projects the page covers (TCW-113 Design 6.6): the scope and the
// one project kept, read from and written to the URL's query string, so a
// link reproduces the view and names the CLI flags it matches.
import type { TScope, TScopeStatus } from "./types"

export const SCOPES: TScope[] = ["own", "up", "down", "all"]

/** What each scope adds, as the scope control labels it. */
export const SCOPE_LABELS: Record<TScope, string> = {
    own: "This project",
    up: "With its ancestors",
    down: "With its descendants",
    all: "Ancestors and descendants",
}

export interface TScopeChoice {
    scope: TScope
    /** The one project whose own objects are kept, as `--project` keeps
     * them; absent for every project the scope covers. */
    project?: string
}

export const OWN: TScopeChoice = { scope: "own" }

/** The scope and project a location's query string names. An unknown
 * scope reads as `own`, the default. */
export function scopeParams(search: string): TScopeChoice {
    const params = new URLSearchParams(search)
    const given = params.get("scope") ?? ""
    const scope = (SCOPES as string[]).includes(given)
        ? (given as TScope)
        : "own"
    const project = params.get("project") || undefined
    return project ? { scope, project } : { scope }
}

/** The query string that names a choice, with its `?`, or "" for the
 * default: `own` and every project. */
export function scopeSearch(choice: TScopeChoice): string {
    const params = new URLSearchParams()
    if (choice.scope !== "own") params.set("scope", choice.scope)
    if (choice.project) params.set("project", choice.project)
    const text = params.toString()
    return text ? `?${text}` : ""
}

/** `path` asking for a choice: its parameters added after any it has. */
export function withScope(path: string, choice: TScopeChoice): string {
    const extra = scopeSearch(choice).slice(1)
    if (!extra) return path
    return `${path}${path.includes("?") ? "&" : "?"}${extra}`
}

/** Each status a row's projects hold, with how many hold it, in the order
 * the statuses first appear (Design 6.9): `Missing(1), Supported(1)`. */
export function statusSummary(statuses: TScopeStatus[]): string {
    const counts = new Map<string, number>()
    for (const entry of statuses) {
        const name = entry.status ?? "(no status)"
        counts.set(name, (counts.get(name) ?? 0) + 1)
    }
    return [...counts].map(([name, count]) => `${name}(${count})`).join(", ")
}
