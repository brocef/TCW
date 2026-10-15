import { encodePath, findingLines, isStaleWrite, isUnavailable } from "./api"

const result = (status: number, code?: string) => ({
    ok: status < 400,
    status,
    data: null,
    error: "",
    code,
})

test("a 409 marked stale-revision is a stale write", () => {
    expect(isStaleWrite(result(409, "stale-revision"))).toBe(true)
})

test.each([
    ["a 409 with another reason", result(409, "refused")],
    ["a 409 with no code", result(409)],
    ["another status carrying the marker", result(422, "stale-revision")],
    ["a success", result(200)],
])("%s is not a stale write", (_label, value) => {
    expect(isStaleWrite(value)).toBe(false)
})

test("a part the backend could not give is unavailable", () => {
    expect(isUnavailable({ unavailable: "Jira is unreachable" })).toBe(true)
    for (const value of [null, [], "x", { title: "t" }, { unavailable: 1 }])
        expect(isUnavailable(value)).toBe(false)
})

test("validation notices read as severity, where and message", () => {
    expect(
        findingLines({
            warnings: [
                { severity: "warning", where: "parent", message: "check it" },
            ],
        })
    ).toEqual(["warning: parent: check it"])
    expect(findingLines({})).toEqual([])
})

test("a file path keeps its slash and encodes each segment", () => {
    expect(encodePath("a b/round-1.md")).toBe("a%20b/round-1.md")
})
