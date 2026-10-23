/** Full identifiers (TCW-110 Design 1.1): the client's one parser of
 * `<project>.<namespace>/<id-path>`, which every record the server sends
 * carries as `full-id`. The server's own parser is `tcw/ids.py`; this one
 * follows the same grammar, so the page never splits a name by hand. */

export const NAMESPACES = ["taxonomy", "capabilities", "work"] as const
export type Namespace = (typeof NAMESPACES)[number]

export interface FullId {
    project: string
    namespace: Namespace
    idPath: string
}

const PROJECT_ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const RESERVED = new Set(["t", "c", "w", "local"])
const ID_PART = /^[A-Za-z0-9][A-Za-z0-9_-]*$/
const ID_PART_LIMIT = 128

function isNamespace(text: string): text is Namespace {
    return (NAMESPACES as readonly string[]).includes(text)
}

function validIdPath(idPath: string): boolean {
    if (!idPath) return false
    return idPath
        .split("/")
        .every((part) => part.length <= ID_PART_LIMIT && ID_PART.test(part))
}

/** The parts of a full identifier, or `null` when the text is not one. */
export function parseFullId(text: string): FullId | null {
    const slash = text.indexOf("/")
    if (slash === -1) return null
    const head = text.slice(0, slash).split(".")
    if (head.length !== 2) return null
    const [project, namespace] = head
    const idPath = text.slice(slash + 1)
    if (!PROJECT_ID.test(project) || RESERVED.has(project)) return null
    if (!isNamespace(namespace) || !validIdPath(idPath)) return null
    return { project, namespace, idPath }
}

/** Whether the text is a valid full identifier. */
export function isFullId(text: string): boolean {
    return parseFullId(text) !== null
}

/** The text of a full identifier. */
export function fullIdText(
    project: string,
    namespace: Namespace,
    idPath: string
): string {
    return `${project}.${namespace}/${idPath}`
}

/** A full identifier's `tcw://` address, the form a Markdown link holds. */
export function objectAddress(fullId: string): string {
    return `tcw://${fullId}`
}

/** The web app's key for an entry (TCW-110 Design 4.5): its id-path when
 * the served project owns it, and its whole full identifier for an
 * inherited one. The server's `route_key` gives the same answer. */
export function routeKey(fullId: string, projectId: string): string {
    const found = parseFullId(fullId)
    if (!found) return fullId
    return found.project === projectId ? found.idPath : fullId
}

/** The segments a route key is shown as in a tree: an inherited entry's
 * full identifier is `<project>.<namespace>` and then its id-path's parts,
 * so one owner's entries sit under one top node; an id-path is its parts. */
export function keySegments(key: string): string[] {
    const found = parseFullId(key)
    if (found)
        return [
            `${found.project}.${found.namespace}`,
            ...found.idPath.split("/"),
        ]
    return key.split("/")
}
