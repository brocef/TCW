// @vitest-environment node
// Node's own URL, not jsdom's: TCW-110 AC 2 names the parser Node ships.
import addresses from "../../../../tests/fixtures/tcw-addresses.json"
import { fullIdText, isFullId, objectAddress, parseFullId } from "./identifier"

describe("parseFullId", () => {
    it.each([
        ["a.taxonomy/x", "a", "taxonomy", "x"],
        ["a-1.capabilities/cli/x_y", "a-1", "capabilities", "cli/x_y"],
        ["p.work/TCW-120-add-login", "p", "work", "TCW-120-add-login"],
    ])("accepts %s", (text, project, namespace, idPath) => {
        expect(parseFullId(text)).toEqual({ project, namespace, idPath })
    })

    it.each([
        "a/x",
        "A.work/x",
        "a.Work/x",
        "a.thing/x",
        "a.work/",
        "a.work//x",
        "a.work/-x",
        "a.work/x.y",
        "a.work/x y",
        "a.work/x%20",
        "local.work/x",
        "a.work/" + "x".repeat(129),
        "x",
    ])("refuses %s", (text) => {
        expect(parseFullId(text)).toBeNull()
        expect(isFullId(text)).toBe(false)
    })
})

describe("building identifiers", () => {
    it("joins a project, a namespace and an id-path", () => {
        expect(fullIdText("demo", "work", "x")).toBe("demo.work/x")
        expect(objectAddress("demo.work/x")).toBe("tcw://demo.work/x")
    })
})

describe("addresses read by Node's URL parser", () => {
    it.each(addresses.accepted)("$address", ({ address, path }) => {
        expect(new URL(address).pathname).toBe(path)
    })
})
