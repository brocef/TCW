// Answers shaped as the server gives them, for the client's unit tests. The
// stage table here is a test's own: the client holds no stage names, so the
// names below could be any words.
import type {
    CapabilityItem,
    TaxonomyItem,
    TProject,
    TStageRow,
    WorkDetail,
    WorkItem,
} from "./model/types"

function row(
    name: string,
    kind: TStageRow["kind"],
    artifact: TStageRow["artifact"],
    extra: Partial<TStageRow> = {}
): TStageRow {
    return {
        name,
        kind,
        artifact,
        verdict: false,
        onReject: null,
        external: false,
        completion: false,
        discard: false,
        ...extra,
    }
}

export const STAGES: TStageRow[] = [
    row("intake", "flow", "none"),
    row("ask", "flow", "document"),
    row("build", "flow", "rounds"),
    row("judge", "flow", "rounds", { verdict: true, onReject: "build" }),
    row("done", "terminal", "none", { completion: true }),
    row("dropped", "terminal", "none", { discard: true }),
    row("lessons", "side", "document"),
]

export function project(overrides: Partial<TProject> = {}): TProject {
    return {
        id: "p",
        recordOwner: "local",
        stages: STAGES,
        inboxStage: "intake",
        startStage: "ask",
        inboxItems: true,
        tags: ["ui", "api"],
        scales: {
            priority: ["highest", "high", "medium", "low", "lowest"],
            size: ["low", "medium", "high", "very-high"],
        },
        capabilityScales: {
            status: ["Missing", "Partial", "Supported"],
            priority: ["P0", "P1"],
            lifecycle: ["Stable"],
        },
        createFields: ["priority", "effort", "complexity"],
        user: "ann",
        people: {},
        axes: { work: true, taxonomy: true, capabilities: true },
        scopes: { own: ["p"], up: ["p"], down: ["p"], all: ["p"] },
        ...overrides,
    }
}

/** A taxonomy record of project `owner` (default `p`, the fixture
 * project). */
export function term(
    slug: string,
    overrides: Partial<TaxonomyItem> = {},
    owner = "p"
): TaxonomyItem {
    return { "full-id": `${owner}.taxonomy/${slug}`, owner, ...overrides }
}

/** A capability record of project `owner` (default `p`). */
export function capability(
    path: string,
    overrides: Partial<CapabilityItem> = {},
    owner = "p"
): CapabilityItem {
    return { "full-id": `${owner}.capabilities/${path}`, owner, ...overrides }
}

export function workItem(
    folder: string,
    overrides: Partial<WorkItem> = {}
): WorkItem {
    return {
        "full-id": `p.work/${folder}`,
        owner: "p",
        title: folder,
        stage: "ask",
        created: "2026-10-01T09:00:00+00:00",
        priority: "medium",
        effort: null,
        complexity: null,
        tags: [],
        assignee: null,
        parent: null,
        "blocked-by": [],
        blocks: [],
        children: [],
        path: `/work/${folder}`,
        untracked: [],
        ...overrides,
    }
}

export function workDetail(
    folder: string,
    overrides: Partial<WorkDetail> = {}
): WorkDetail {
    return {
        folder,
        item: workItem(folder),
        comments: [],
        commentsLimited: false,
        people: {},
        link: null,
        files: [
            {
                stage: "ask",
                artifact: "document",
                verdict: false,
                document: {
                    path: "ask/ask.md",
                    revision: null,
                    present: false,
                },
                handoffs: [],
            },
            {
                stage: "build",
                artifact: "rounds",
                verdict: false,
                rounds: [],
                handoffs: [],
            },
            {
                stage: "judge",
                artifact: "rounds",
                verdict: true,
                rounds: [],
                handoffs: [],
            },
            {
                stage: "lessons",
                artifact: "document",
                verdict: false,
                document: {
                    path: "lessons/lessons.md",
                    revision: null,
                    present: false,
                },
                handoffs: [],
            },
            {
                stage: null,
                artifact: "declaration",
                document: {
                    path: "capabilities.yaml",
                    revision: null,
                    present: false,
                },
            },
        ],
        verdicts: [{ stage: "judge", verdict: "none" }],
        warnings: [],
        ...overrides,
    }
}

/** A `fetch` answering by path: each entry is `[match, status, body]`, the
 * first whose `match` the request path starts with (or equals, for a
 * string ending in `$`) wins. Requests are recorded on `calls`. */
export function fakeFetch(
    routes: Array<[string | RegExp, number, unknown]>
): ReturnType<typeof vi.fn> & {
    calls: Array<{ path: string; method: string; body: unknown }>
} {
    const calls: Array<{ path: string; method: string; body: unknown }> = []
    const fn = vi.fn(async (input: unknown, init?: RequestInit) => {
        const path = String(input)
        const method = init?.method ?? "GET"
        calls.push({
            path,
            method,
            body: init?.body ? JSON.parse(String(init.body)) : undefined,
        })
        const found = routes.find(([match]) =>
            typeof match === "string"
                ? match.endsWith("$")
                    ? path === match.slice(0, -1)
                    : path.startsWith(match)
                : match.test(`${method} ${path}`)
        )
        const [, status, body] = found ?? [path, 404, { error: "not found" }]
        return {
            ok: status < 400,
            status,
            statusText: String(status),
            json: async () => body,
        }
    })
    return Object.assign(fn, { calls })
}
