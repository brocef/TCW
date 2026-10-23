import { parseFullId } from "./identifier"
import type { JsonRecord, TBoard, TProject, TStageRow, WorkItem } from "./types"

/** The stage filter's value for an item with no stage: a Jira ticket in a
 * status no stage maps to. Not a stage name, so it cannot collide with one. */
export const NO_STAGE = "(no stage)"

/** The folder of a work item's full identifier (`<project>.work/<folder>`),
 * or the text itself when it is a bare folder name. */
export function folderOf(fullId: string): string {
    return parseFullId(fullId)?.idPath ?? fullId
}

/** The project of a full identifier, or `null` for a bare folder name. */
export function projectOf(fullId: string): string | null {
    return parseFullId(fullId)?.project ?? null
}

/** A person as the page shows them: the backend's display name when the
 * answer carried one, else the stored value (a name, or an account ID). */
export function personName(
    id: string | null | undefined,
    people: Record<string, string>
): string {
    if (!id) return ""
    return people[id] ?? id
}

/** What `tcw work list` shows by default: every stage that is not terminal,
 * and items with no stage. */
export function defaultStageFilter(
    stages: TStageRow[]
): Record<string, boolean> {
    return Object.fromEntries([
        ...stages.map((row) => [row.name, row.kind !== "terminal"]),
        [NO_STAGE, true],
    ])
}

/** Whether the board must be loaded with `all=1`: a terminal stage is
 * ticked, and the default query leaves terminal stages out. */
export function needsAll(
    filter: Record<string, boolean>,
    stages: TStageRow[]
): boolean {
    return stages.some((row) => row.kind === "terminal" && filter[row.name])
}

/** The board's query string: `all=1` when needed, one `tag` per ticked tag. */
export function boardQuery(all: boolean, tags: string[]): string {
    const parts = [
        ...(all ? ["all=1"] : []),
        ...tags.map((tag) => `tag=${encodeURIComponent(tag)}`),
    ]
    return parts.length ? `?${parts.join("&")}` : ""
}

/** The board's rows as item records. A fallback row, which carries only its
 * folder, becomes a record with nothing known and `unread` set. */
export function boardRows(board: TBoard): WorkItem[] {
    return board.items.map((row) =>
        "title" in row
            ? row
            : {
                  "full-id": row["full-id"],
                  owner: row.owner,
                  path: row.path,
                  title: folderOf(row["full-id"]),
                  stage: null,
                  created: "",
                  priority: null,
                  effort: null,
                  complexity: null,
                  tags: [],
                  assignee: null,
                  parent: null,
                  "blocked-by": [],
                  blocks: [],
                  children: [],
                  untracked: [],
                  unread: true,
              }
    )
}

/** Whether a row passes the stage filter. */
export function stageShown(
    item: WorkItem,
    filter: Record<string, boolean>
): boolean {
    if (item.unread) return true
    return filter[item.stage ?? NO_STAGE] !== false
}

/** The assignees the filter offers: everyone on the loaded rows, and the
 * current user. */
export function knownAssignees(
    items: WorkItem[],
    user: string | null
): string[] {
    const found = new Set<string>()
    for (const item of items) if (item.assignee) found.add(item.assignee)
    if (user) found.add(user)
    return [...found].sort((left, right) => left.localeCompare(right))
}

/** The verdict a stage's rounds give, as the server computed it. */
export function stageVerdict(
    verdicts: Array<{ stage: string; verdict: string }>,
    stage: string
): string | undefined {
    return verdicts.find((entry) => entry.stage === stage)?.verdict
}

/** Whether a full identifier names an item of this project. */
export function isLocal(fullId: string, project: TProject): boolean {
    const owner = projectOf(fullId)
    return owner === null || owner === project.id
}

/** The sentence the stage line carries: the viewer never moves an item. */
export function moveHint(fullId: string): string {
    return `Move it with \`tcw work advance ${fullId}\`.`
}

/** The `verdict:` value in a round's front matter, or "" when unset. */
export function verdictLine(text: string): string {
    const front = /^---\n([\s\S]*?)\n---(?:\n|$)/.exec(text)
    if (!front) return ""
    const line = /^verdict:[ \t]*(.*)$/m.exec(front[1])
    return line ? line[1].trim() : ""
}

/** `text` with its front matter's `verdict:` line set to `verdict` (empty
 * leaves it unset). A round with no front matter gains one. */
export function withVerdict(text: string, verdict: string): string {
    const value = verdict ? `verdict: ${verdict}` : "verdict:"
    const front = /^---\n([\s\S]*?)\n---(\n|$)/.exec(text)
    if (!front) return `---\n${value}\n---\n${text}`
    const body = /^verdict:.*$/m.test(front[1])
        ? front[1].replace(/^verdict:.*$/m, value)
        : `${front[1]}\n${value}`
    return `---\n${body}\n---${front[2]}${text.slice(front[0].length)}`
}

/** A stage's name as a tab label: the table's own word, capitalized. */
export function stageLabel(name: string): string {
    return name ? name[0].toUpperCase() + name.slice(1) : name
}

function sameList(left: string[], right: string[]) {
    return [...left].sort().join("\n") === [...right].sort().join("\n")
}

export type TPropertiesDraft = {
    title: string
    priority: string
    effort: string
    complexity: string
    assignee: string
    parent: string
    tags: string[]
    "blocked-by": string[]
}

/** A properties form's starting values: the record as loaded. */
export function propertiesDraft(item: WorkItem): TPropertiesDraft {
    return {
        title: item.title,
        priority: item.priority ?? "",
        effort: item.effort ?? "",
        complexity: item.complexity ?? "",
        assignee: item.assignee ?? "",
        parent: item.parent ?? "",
        tags: [...item.tags],
        "blocked-by": [...item["blocked-by"]],
    }
}

/** The changes a properties form sends, and the loaded values it expects:
 * only the properties it changed, so nothing else is ever overwritten. */
export function propertyChanges(
    item: WorkItem,
    draft: TPropertiesDraft
): { changes: JsonRecord; expected: JsonRecord } {
    const loaded = propertiesDraft(item)
    const changes: JsonRecord = {}
    const expected: JsonRecord = {}
    for (const name of [
        "title",
        "priority",
        "effort",
        "complexity",
        "assignee",
        "parent",
    ] as const) {
        if (draft[name].trim() === loaded[name]) continue
        changes[name] =
            name === "title" ? draft[name].trim() : draft[name].trim() || null
        expected[name] = item[name]
    }
    for (const name of ["tags", "blocked-by"] as const) {
        if (sameList(draft[name], loaded[name])) continue
        changes[name] = {
            add: draft[name].filter((value) => !loaded[name].includes(value)),
            remove: loaded[name].filter(
                (value) => !draft[name].includes(value)
            ),
        }
        expected[name] = item[name]
    }
    return { changes, expected }
}
