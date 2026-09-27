import { isStaleWrite } from "./api"

const result = (status: number, data: Record<string, unknown> | null) => ({
    ok: status < 400,
    status,
    data,
    error: typeof data?.error === "string" ? data.error : "",
})

test("a 409 marked stale-revision is a stale write", () => {
    expect(
        isStaleWrite(result(409, { error: "stale", code: "stale-revision" }))
    ).toBe(true)
})

test.each([
    [
        "a 409 with another reason",
        result(409, { error: "run tcw work tracker" }),
    ],
    ["a 409 with no body", result(409, null)],
    [
        "another status carrying the marker",
        result(422, { code: "stale-revision" }),
    ],
    ["a success", result(200, {})],
])("%s is not a stale write", (_label, value) => {
    expect(isStaleWrite(value)).toBe(false)
})
