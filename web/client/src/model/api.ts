import type { TReferenceOption } from "./reference-search"
import type { ApiResult, TFinding, TUnavailable } from "./types"

/** A failed answer from the server, carrying its HTTP status, so a caller
 * can tell "not found" from every other failure. */
export class HttpError extends Error {
    readonly status: number
    constructor(message: string, status: number) {
        super(message)
        this.name = "HttpError"
        this.status = status
    }
}

/** The message for a request that got no answer at all, such as when the
 * server has stopped. */
export function unreachableMessage(failure: unknown): string {
    const reason = failure instanceof Error ? failure.message : String(failure)
    return `Could not reach the tcw serve process (${reason}). Is it still running?`
}

/** A GET. A failed answer throws an `HttpError` with the server's own
 * message, which names what went wrong; the status line alone does not. */
export async function fetchJson<T>(path: string): Promise<T> {
    const response = await fetch(path)
    if (!response.ok) {
        let message = `${response.status} ${response.statusText}`
        try {
            const body = (await response.json()) as { error?: unknown }
            if (typeof body.error === "string" && body.error)
                message = body.error
        } catch {
            // not JSON: the status line is all there is
        }
        throw new HttpError(message, response.status)
    }
    return response.json() as Promise<T>
}

/** A write. It never throws: a request that got no answer (the server has
 * stopped, the network failed) is a failed result with status 0 and a
 * message saying so, so every form shows it as it shows a refusal. */
export async function requestJson<T>(
    path: string,
    method: "POST" | "PATCH" | "PUT",
    body?: unknown
): Promise<ApiResult<T>> {
    let response: Response
    try {
        response = await fetch(path, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body ?? {}),
        })
    } catch (failure) {
        return {
            ok: false,
            status: 0,
            data: null,
            error: unreachableMessage(failure),
            code: "unreachable",
        }
    }
    try {
        const data = (await response.json()) as T & {
            error?: string
            code?: string
        }
        return {
            ok: response.ok,
            status: response.status,
            data,
            error: data.error ?? response.statusText,
            code: data.code,
        }
    } catch {
        return {
            ok: response.ok,
            status: response.status,
            data: null,
            error: response.statusText,
        }
    }
}

export const encodeRef = (value: string) => encodeURIComponent(value)

/** A file path inside an item (`<stage>/<file>`), each segment encoded and
 * the `/` kept, as the files route reads it. */
export const encodePath = (value: string) =>
    value.split("/").map(encodeURIComponent).join("/")

/** Whether a failed save was refused for a stale revision — the one refusal the
 * conflict banner answers. The server answers 409 for other refusals too, and
 * those show their message. */
export function isStaleWrite(result: ApiResult<unknown>): boolean {
    return result.status === 409 && result.code === "stale-revision"
}

/** Whether a part of an answer is the backend's "could not answer". */
export function isUnavailable(value: unknown): value is TUnavailable {
    return (
        typeof value === "object" &&
        value !== null &&
        !Array.isArray(value) &&
        typeof (value as TUnavailable).unavailable === "string"
    )
}

/** A save's validation notices, as `severity: where: message`. */
export function findingLines(data: unknown): string[] {
    const warnings = (data as { warnings?: unknown } | null)?.warnings
    if (!Array.isArray(warnings)) return []
    return warnings.map((entry) => {
        if (typeof entry === "string") return entry
        const finding = entry as TFinding
        return [finding.severity, finding.where, finding.message]
            .filter(Boolean)
            .join(": ")
    })
}

/** Items of connected filesystem-mode projects found on this machine, for
 * a parent or blocked-by field. */
export async function suggestOtherItems(
    text: string
): Promise<TReferenceOption[]> {
    const found = await fetchJson<
        Array<{ slug: string; title: string; project: string }>
    >(`/api/options/work?q=${encodeURIComponent(text)}`)
    return found.map((item) => ({
        identifier: item.slug,
        displayName: `${item.title} (${item.project})`,
    }))
}

/** The people the backend lets an item be assigned to, by display name. */
export async function suggestAssignees(
    text: string
): Promise<TReferenceOption[]> {
    const found = await fetchJson<Array<{ id: string; name: string }>>(
        `/api/options/assignee?q=${encodeURIComponent(text)}`
    )
    return found.map((person) => ({
        identifier: person.id,
        displayName: person.name,
    }))
}
