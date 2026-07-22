import { expect, test, vi } from "vitest"
import { openWorkResource } from "./work-resource"

test("sends valid JSON when opening a plan-stage document", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 204 })
    globalThis.fetch = fetchMock
    const toast = vi.fn()

    await openWorkResource("example/item", "build-ui", "plan-stages", toast)

    expect(fetchMock).toHaveBeenCalledWith(
        "/api/work/example%2Fitem/plan-stages/build-ui/open",
        {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: "{}",
        }
    )
    expect(toast).toHaveBeenCalledWith("Opened resource")
})
