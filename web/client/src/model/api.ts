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
