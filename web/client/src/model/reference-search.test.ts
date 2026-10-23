import { describe, expect, test } from "vitest"
import {
    declarationField,
    highlightMatches,
    otherProjectWarning,
    pathSegments,
    rankReferenceOptions,
    referenceOptions,
    tcwLinkOptions,
    typedLink,
    type TReferenceOption,
} from "./reference-search"
import { workItem } from "../test-fixtures"

const choices: TReferenceOption[] = [
    { displayName: "Useful editor", identifier: "web/use" },
    { displayName: "Use", identifier: "commands/long-identifier" },
    { displayName: "Unused", identifier: "use" },
]

describe("reference search", () => {
    test("uses weighted name and identifier ranking with deterministic ties", () => {
        const ranked = rankReferenceOptions(choices, " use ")
        expect(ranked.map((item) => item.identifier)).toEqual([
            "use",
            "web/use",
            "commands/long-identifier",
        ])
        const ties = rankReferenceOptions(
            [
                { displayName: "Same", identifier: "z/use" },
                { displayName: "Same", identifier: "a/use" },
            ],
            "same"
        )
        expect(ties.map((item) => item.identifier)).toEqual(["a/use", "z/use"])
    })

    test("matches case-insensitively, limits results, and highlights every substring", () => {
        expect(
            rankReferenceOptions(
                Array.from({ length: 12 }, (_, index) => ({
                    displayName: `USE ${index}`,
                    identifier: `item-${index}`,
                })),
                "use"
            )
        ).toHaveLength(10)
        expect(
            highlightMatches("Use use USE", "use")
                .filter((part) => part.matched)
                .map((part) => part.text)
        ).toEqual(["Use", "use", "USE"])
    })

    test("applies centralized candidate restrictions and duplicate filtering", () => {
        const context = {
            currentIdentifier: "p.work/parent",
            selected: ["p.work/duplicate"],
            work: [
                workItem("parent"),
                workItem("child", { parent: "p.work/parent" }),
                workItem("epic"),
                workItem("duplicate"),
            ],
            taxonomy: [
                { slug: "term", name: "Term", kind: "Vocabulary" },
                { slug: "feature", name: "Feature", kind: "Feature" },
            ],
            capabilities: [
                { path: "roles/admin", name: "Admin" },
                { path: "conditions/online", name: "Online" },
                { path: "parent", name: "Current" },
            ],
        }
        expect(
            referenceOptions("work-parent", context).map(
                (item) => item.identifier
            )
        ).toEqual(["p.work/epic", "p.work/duplicate"])
        expect(
            referenceOptions("work-blockers", context).map(
                (item) => item.identifier
            )
        ).toEqual(["p.work/child", "p.work/epic"])
        expect(
            referenceOptions("taxonomy-vocabulary", context).map(
                (item) => item.identifier
            )
        ).toEqual(["term"])
        expect(
            referenceOptions("capability-roles", context).map(
                (item) => item.identifier
            )
        ).toEqual(["roles/admin"])
        expect(
            referenceOptions("capability-when", context).map(
                (item) => item.identifier
            )
        ).toEqual(["conditions/online"])
    })
})

describe("the fields of the autocomplete table", () => {
    const context = {
        work: [
            workItem("parent"),
            workItem("child", { parent: "p.work/parent" }),
            workItem("grandchild", { parent: "p.work/child" }),
            workItem("other", { assignee: "acc-1" }),
        ],
        taxonomy: [
            { slug: "term", name: "Term", kind: "Vocabulary" },
            {
                slug: "shared",
                qualified: "base/shared",
                name: "Shared",
                kind: "Vocabulary",
                origin: "base",
            },
            { slug: "feature", name: "Feature", kind: "Feature" },
        ],
        capabilities: [
            { path: "roles/admin", name: "Admin" },
            {
                path: "roles/guest",
                qualified: "base/roles/guest",
                name: "Guest",
                origin: "base",
            },
            { path: "web/editing", name: "Editing" },
            { path: "web/reading", name: "Reading" },
        ],
        people: { "acc-1": "Ann" },
        user: "acc-me",
    }
    const ids = (field: Parameters<typeof referenceOptions>[0], extra = {}) =>
        referenceOptions(field, { ...context, ...extra }).map(
            (item) => item.identifier
        )

    test("a work parent excludes the item and its descendants", () => {
        expect(
            ids("work-parent", { currentIdentifier: "p.work/parent" })
        ).toEqual(["p.work/other"])
    })

    test("assignees are the names on items and the user", () => {
        const found = referenceOptions("work-assignee", context)
        expect(found).toEqual([
            { identifier: "acc-1", displayName: "Ann" },
            { identifier: "acc-me", displayName: "acc-me (me)" },
        ])
    })

    test("a subject and a feature's vocabulary are vocabulary entries, inherited included", () => {
        expect(ids("capability-subject")).toEqual(["term", "base/shared"])
        expect(ids("taxonomy-vocabulary")).toEqual(["term", "base/shared"])
        expect(ids("capability-feature")).toEqual(["feature"])
    })

    test("roles are roles capabilities by path, inherited included", () => {
        expect(ids("capability-roles")).toEqual(["roles/admin", "roles/guest"])
    })

    test("declaration lists offer the ledger's entries", () => {
        expect(ids(declarationField("capabilities", "changed"))).toContain(
            "web/editing"
        )
        expect(ids(declarationField("taxonomy", "new"))).toContain(
            "base/shared"
        )
    })
})

test("a capability path is offered one segment at a time", () => {
    const paths = ["web/editing", "web/reading/fast", "cli/help"]
    expect(pathSegments(paths, "").map((item) => item.identifier)).toEqual([
        "web",
        "cli",
    ])
    expect(
        pathSegments(paths, "web/re").map((item) => item.identifier)
    ).toEqual(["web/editing", "web/reading"])
    expect(
        pathSegments(paths, "web/reading/").map((item) => item.identifier)
    ).toEqual(["web/reading/fast"])
})

test("tcw:// completion names a work item by its folder, and every axis", () => {
    const found = tcwLinkOptions({
        work: [workItem("2026-10-01-x", { title: "X" })],
        taxonomy: [{ slug: "t", qualified: "base/t", name: "T" }],
        capabilities: [{ path: "web", name: "Web" }],
    })
    expect(found.map((item) => item.identifier)).toEqual([
        "tcw://W/2026-10-01-x",
        "tcw://T/base/t",
        "tcw://C/web",
    ])
})

test("the link being typed is found before the caret", () => {
    expect(typedLink("See tcw://W/20")).toBe("tcw://W/20")
    expect(typedLink("See [x](tcw://C/we")).toBe("tcw://C/we")
    expect(typedLink("See tcw://W/x done")).toBeNull()
})

test("another project's full identifier is kept with a warning; this project's is not", () => {
    expect(otherProjectWarning("q.work/2026-01-01-x", "p")).toMatch(/project q/)
    expect(otherProjectWarning("p.work/2026-01-01-x", "p")).toBeNull()
    expect(otherProjectWarning("q/" + "2026-01-01-x", "p")).toBeNull()
    expect(otherProjectWarning("2026-01-01-x", "p")).toBeNull()
    expect(otherProjectWarning("not a slug", "p")).toBeNull()
})
