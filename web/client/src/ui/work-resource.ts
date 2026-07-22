import { encodeRef } from "../model/api"

export async function openWorkResource(
    slug: string,
    name: string,
    kind: "artifacts" | "plan-stages",
    toast: (message: string) => void
) {
    try {
        const response = await fetch(
            `/api/work/${encodeRef(slug)}/${kind}/${encodeRef(name)}/open`,
            {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: "{}",
            }
        )
        if (!response.ok)
            throw new Error(`${response.status} ${response.statusText}`)
        if (response.status === 204) {
            toast("Opened resource")
            return
        }
        const payload = (await response.json()) as { url?: string }
        if (payload.url) window.open(payload.url, "_blank", "noopener")
    } catch (error) {
        toast(
            `Could not open resource: ${error instanceof Error ? error.message : String(error)}`
        )
    }
}
