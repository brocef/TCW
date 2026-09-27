import type { ApiResult } from "./types"

export async function fetchJson<T>(path: string): Promise<T> {
    const response = await fetch(path)
    if (!response.ok)
        throw new Error(`${response.status} ${response.statusText}`)
    return response.json() as Promise<T>
}

export async function requestJson<T>(
    path: string,
    method: "POST" | "PATCH" | "PUT" | "DELETE",
    body?: unknown
): Promise<ApiResult<T>> {
    const response = await fetch(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body:
            body === undefined && method !== "DELETE"
                ? undefined
                : JSON.stringify(body ?? {}),
    })
    try {
        const data = (await response.json()) as T & { error?: string }
        return {
            ok: response.ok,
            status: response.status,
            data,
            error: data.error ?? response.statusText,
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

/** Whether a failed save was refused for a stale revision — the one refusal the
 * conflict banner answers. The server answers 409 for other refusals too (a
 * strict tracker, a sidecar a command writes), and those show their message. */
export function isStaleWrite(result: ApiResult<unknown>): boolean {
    const data = result.data as { code?: unknown } | null
    return result.status === 409 && data?.code === "stale-revision"
}
