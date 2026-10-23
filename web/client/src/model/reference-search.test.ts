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
import { capability, term, workItem } from "../test-fixtures"

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
                term("term", { name: "Term", kind: "Vocabulary" }),
                term("feature", { name: "Feature", kind: "Feature" }),
            ],
            capabilities: [
                capability("roles/admin", { name: "Admin" }),
                capability("conditions/online", { name: "Online" }),
                capability("parent", { name: "Current" }),
            ],
            projectId: "p",
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
        ).toEqual(["p.taxonomy/term"])
        expect(
            referenceOptions("capability-roles", context).map(
                (item) => item.identifier
            )
        ).toEqual(["p.capabilities/roles/admin"])
        expect(
            referenceOptions("capability-when", context).map(
                (item) => item.identifier
            )
        ).toEqual(["p.capabilities/conditions/online"])
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
            term("term", { name: "Term", kind: "Vocabulary" }),
            term("shared", { name: "Shared", kind: "Vocabulary" }, "base"),
            term("feature", { name: "Feature", kind: "Feature" }),
        ],
        capabilities: [
            capability("roles/admin", { name: "Admin" }),
            capability("roles/guest", { name: "Guest" }, "base"),
            capability("web/editing", { name: "Editing" }),
            capability("web/reading", { name: "Reading" }),
        ],
        people: { "acc-1": "Ann" },
        user: "acc-me",
        projectId: "p",
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
        // TCW-110 Design 5.1: the value a picker inserts is the full identifier.
        expect(ids("capability-subject")).toEqual([
            "p.taxonomy/term",
            "base.taxonomy/shared",
        ])
        expect(ids("taxonomy-vocabulary")).toEqual([
            "p.taxonomy/term",
            "base.taxonomy/shared",
        ])
        expect(ids("capability-feature")).toEqual(["p.taxonomy/feature"])
    })

    test("roles are roles capabilities, inherited included", () => {
        expect(ids("capability-roles")).toEqual([
            "p.capabilities/roles/admin",
            "base.capabilities/roles/guest",
        ])
    })

    test("a capability's own entry is left out by its route key", () => {
        expect(
            ids("capability-blocked-by", { currentIdentifier: "web/editing" })
        ).toEqual([
            "p.capabilities/roles/admin",
            "base.capabilities/roles/guest",
            "p.capabilities/web/reading",
        ])
    })

    test("a taxonomy parent is a folder of this project's own store", () => {
        expect(ids("taxonomy-parent")).toEqual(["term", "feature"])
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

test("tcw:// completion offers each object's address, in every namespace", () => {
    const found = tcwLinkOptions({
        projectId: "p",
        work: [workItem("2026-10-01-x", { title: "X" })],
        taxonomy: [term("t", { name: "T" }, "base")],
        capabilities: [capability("web", { name: "Web" })],
    })
    expect(found.map((item) => item.identifier)).toEqual([
        "tcw://p.work/2026-10-01-x",
        "tcw://base.taxonomy/t",
        "tcw://p.capabilities/web",
    ])
})

test("the link being typed is found before the caret", () => {
    expect(typedLink("See tcw://p.work/20")).toBe("tcw://p.work/20")
    expect(typedLink("See [x](tcw://p.capabilities/we")).toBe(
        "tcw://p.capabilities/we"
    )
    expect(typedLink("See tcw://p.work/x done")).toBeNull()
})

test("another project's full identifier is kept with a warning; this project's is not", () => {
    expect(otherProjectWarning("q.work/2026-01-01-x", "p")).toMatch(/project q/)
    expect(otherProjectWarning("p.work/2026-01-01-x", "p")).toBeNull()
    expect(otherProjectWarning("q/" + "2026-01-01-x", "p")).toBeNull()
    expect(otherProjectWarning("2026-01-01-x", "p")).toBeNull()
    expect(otherProjectWarning("not a slug", "p")).toBeNull()
})
