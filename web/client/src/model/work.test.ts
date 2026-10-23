import { describe, expect, test } from "vitest"
import {
    NO_STAGE,
    boardQuery,
    boardRows,
    defaultStageFilter,
    folderOf,
    isLocal,
    knownAssignees,
    moveHint,
    needsAll,
    personName,
    projectOf,
    propertyChanges,
    propertiesDraft,
    stageLabel,
    stageShown,
    verdictLine,
    withVerdict,
} from "./work"
import { STAGES, project, workItem } from "../test-fixtures"

test("a full identifier's folder and project", () => {
    expect(folderOf("p.work/2026-01-01-x")).toBe("2026-01-01-x")
    expect(folderOf("2026-01-01-x")).toBe("2026-01-01-x")
    expect(projectOf("q.work/2026-01-01-x")).toBe("q")
    expect(projectOf("2026-01-01-x")).toBeNull()
})

test("TCW-110 AC 20a: this project's items and another's", () => {
    const demo = project({ id: "demo" })
    expect(isLocal("demo.work/x", demo)).toBe(true)
    expect(isLocal("core.work/x", demo)).toBe(false)
    expect(projectOf("demo.work/x")).toBe("demo")
    expect(folderOf("demo.work/x")).toBe("x")
})

test("a person reads by display name when the answer carried one", () => {
    expect(personName("acc-1", { "acc-1": "Ann" })).toBe("Ann")
    expect(personName("acc-2", { "acc-1": "Ann" })).toBe("acc-2")
    expect(personName(null, {})).toBe("")
})

describe("the stage filter", () => {
    test("by default ticks every stage that is not terminal, and no stage", () => {
        const filter = defaultStageFilter(STAGES)
        expect(
            STAGES.filter((row) => filter[row.name]).map((row) => row.kind)
        ).not.toContain("terminal")
        expect(
            STAGES.filter((row) => !filter[row.name]).every(
                (row) => row.kind === "terminal"
            )
        ).toBe(true)
        expect(filter[NO_STAGE]).toBe(true)
        expect(needsAll(filter, STAGES)).toBe(false)
    })

    test("ticking a terminal stage loads every item", () => {
        const terminal = STAGES.find((row) => row.kind === "terminal")!
        const filter = { ...defaultStageFilter(STAGES), [terminal.name]: true }
        expect(needsAll(filter, STAGES)).toBe(true)
    })

    test("an item with no stage is shown under the no-stage value", () => {
        expect(
            stageShown(workItem("x", { stage: null }), { [NO_STAGE]: true })
        ).toBe(true)
        expect(
            stageShown(workItem("x", { stage: null }), { [NO_STAGE]: false })
        ).toBe(false)
    })
})

test("the board query carries all and one tag parameter per tag", () => {
    expect(boardQuery(false, [])).toBe("")
    expect(boardQuery(true, [])).toBe("?all=1")
    expect(boardQuery(false, ["a", "b c"])).toBe("?tag=a&tag=b%20c")
})

test("a fallback row becomes a record that says it was not read", () => {
    const rows = boardRows({
        items: [
            {
                "full-id": "p.work/2026-01-01-x",
                owner: "p",
                path: "/w/2026-01-01-x",
            },
        ],
        people: {},
        fallback: true,
        unavailable: "Jira is unreachable",
    })
    expect(rows[0]).toMatchObject({
        "full-id": "p.work/2026-01-01-x",
        title: "2026-01-01-x",
        stage: null,
        unread: true,
    })
    expect(stageShown(rows[0], { [NO_STAGE]: false })).toBe(true)
})

test("the assignee filter offers everyone on the rows and the user", () => {
    expect(
        knownAssignees(
            [
                workItem("a", { assignee: "bob" }),
                workItem("b", { assignee: null }),
            ],
            "ann"
        )
    ).toEqual(["ann", "bob"])
})

test("the stage line names the command that moves an item", () => {
    expect(moveHint("p.work/2026-01-01-x")).toBe(
        "Move it with `tcw work advance p.work/2026-01-01-x`."
    )
})

test("a stage label is the table's word, capitalized", () => {
    expect(stageLabel("lessons")).toBe("Lessons")
})

describe("a round's verdict line", () => {
    const template = "---\njudges: 2\nverdict:\n---\n"

    test("reads unset from the template, and set once chosen", () => {
        expect(verdictLine(template)).toBe("")
        const chosen = withVerdict(template, "accepted")
        expect(chosen).toBe("---\njudges: 2\nverdict: accepted\n---\n")
        expect(verdictLine(chosen)).toBe("accepted")
    })

    test("keeps the text after the front matter", () => {
        const text = withVerdict(`${template}Looks right.\n`, "rejected")
        expect(text).toBe(
            "---\njudges: 2\nverdict: rejected\n---\nLooks right.\n"
        )
        expect(verdictLine(withVerdict(text, ""))).toBe("")
    })

    test("gives a round without front matter one", () => {
        expect(withVerdict("Body\n", "accepted")).toBe(
            "---\nverdict: accepted\n---\nBody\n"
        )
    })
})

describe("a properties save", () => {
    const item = workItem("x", {
        priority: "medium",
        tags: ["ui"],
        "blocked-by": ["p/a"],
        assignee: "ann",
    })

    test("sends only what changed, each with the value loaded", () => {
        const draft = {
            ...propertiesDraft(item),
            priority: "high",
            assignee: "",
            tags: ["api"],
        }
        expect(propertyChanges(item, draft)).toEqual({
            changes: {
                priority: "high",
                assignee: null,
                tags: { add: ["api"], remove: ["ui"] },
            },
            expected: { priority: "medium", assignee: "ann", tags: ["ui"] },
        })
    })

    test("an unchanged form sends nothing", () => {
        expect(propertyChanges(item, propertiesDraft(item))).toEqual({
            changes: {},
            expected: {},
        })
    })
})
