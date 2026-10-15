import { useEffect, useState } from "react"
import {
    Button,
    Callout,
    Checkbox,
    Flex,
    Heading,
    Text,
    TextArea,
} from "@radix-ui/themes"
import {
    encodePath,
    encodeRef,
    fetchJson,
    HttpError,
    isStaleWrite,
    isUnavailable,
    requestJson,
    suggestAssignees,
    suggestOtherItems,
} from "../model/api"
import {
    propertiesDraft,
    propertyChanges,
    verdictLine,
    withVerdict,
    type TPropertiesDraft,
} from "../model/work"
import type {
    JsonRecord,
    TFileContent,
    TProject,
    TTicket,
    WorkItem,
} from "../model/types"
import { Conflict, EditorHeader } from "./content-views"
import { ReferenceInput } from "./reference-input"
import { RefusalContext, useRefusals } from "./refusals"
import {
    Errors,
    MarkdownEditor,
    SelectInput,
    TextInput,
} from "./shared-components"
import {
    otherProjectWarning,
    referenceOptions,
    type TReferenceContext,
} from "../model/reference-search"

/** What a form reports when it saved: a toast line and the server's answer,
 * whose validation notices the page shows. */
export type TSaved = (message: string, response: unknown) => void

const VERDICTS = ["", "accepted", "rejected"]

export type TFileSession = {
    folder: string
    stage: string
    path: string
    /** null: the file does not exist yet, and saving creates it. */
    revision: string | null
    content: string
    /** A round of a stage whose rounds carry a verdict. */
    verdict: boolean
}

/** A document, round or handoff in the Markdown editor. A verdict round's
 * verdict is a fixed choice above the editor, written to its `verdict:`
 * line. A stale save keeps the draft and offers to load the file again. */
export function FileEditor({
    session,
    onSaved,
    onCancel,
    onDirty,
}: {
    session: TFileSession
    onSaved: TSaved
    onCancel: () => void
    onDirty: (dirty: boolean) => void
}) {
    const [draft, setDraft] = useState(session.content)
    const [revision, setRevision] = useState(session.revision)
    const [saving, setSaving] = useState(false)
    const [errors, setErrors] = useState<string[]>([])
    const [stale, setStale] = useState(false)
    const change = (next: string) => {
        setDraft(next)
        onDirty(true)
    }
    const url = `/api/work/${encodeRef(session.folder)}/files/${encodePath(session.path)}`
    const save = async () => {
        setSaving(true)
        setErrors([])
        try {
            const result = await requestJson<JsonRecord>(url, "PUT", {
                content: draft,
                revision,
            })
            if (isStaleWrite(result)) {
                setStale(true)
                return
            }
            if (!result.ok) {
                setErrors([result.error || `Save failed (${result.status})`])
                return
            }
            onDirty(false)
            onSaved(`${session.path} saved`, result.data)
        } finally {
            setSaving(false)
        }
    }
    const reload = async () => {
        if (!window.confirm("Replace your draft with the file as it is now?"))
            return
        try {
            const found = await fetchJson<TFileContent>(url)
            setDraft(found.content)
            setRevision(found.revision)
            onDirty(false)
        } catch (failure) {
            if (!(failure instanceof HttpError && failure.status === 404)) {
                // Not read: keep the draft and the conflict, and say why.
                setErrors([
                    failure instanceof Error
                        ? failure.message
                        : String(failure),
                ])
                return
            }
            // The file is gone: saving the draft creates it afresh.
            setRevision(null)
        }
        setErrors([])
        setStale(false)
    }
    return (
        <div className={`editor-container${saving ? " saving" : ""}`}>
            <EditorHeader
                title={`${revision === null ? "Create" : "Edit"} ${session.path}`}
                saving={saving}
                onSave={() => void save()}
                onCancel={onCancel}
            />
            <Errors errors={errors} />
            {stale && (
                <Conflict
                    onRefresh={() => void reload()}
                    onDiscard={onCancel}
                />
            )}
            {session.verdict && (
                <SelectInput
                    label="Verdict"
                    value={verdictLine(draft)}
                    options={VERDICTS}
                    onChange={(value) => change(withVerdict(draft, value))}
                />
            )}
            <MarkdownEditor value={draft} onChange={change} />
        </div>
    )
}

/** The item's properties, in filesystem mode. */
export function PropertiesForm({
    project,
    item,
    folder,
    references,
    onSaved,
    onCancel,
    onDirty,
    onReload,
}: {
    project: TProject
    item: WorkItem
    folder: string
    references: TReferenceContext
    onSaved: TSaved
    onCancel: () => void
    onDirty: (dirty: boolean) => void
    onReload: () => void
}) {
    const [draft, setDraftState] = useState(() => propertiesDraft(item))
    const [saving, setSaving] = useState(false)
    const [errors, setErrors] = useState<string[]>([])
    const [stale, setStale] = useState("")
    const refusals = useRefusals()
    const set = (name: keyof TPropertiesDraft, value: unknown) => {
        setDraftState((old) => ({ ...old, [name]: value }))
        onDirty(true)
    }
    const save = async () => {
        if (refusals.pending.length) {
            setErrors(refusals.pending)
            return
        }
        const { changes, expected } = propertyChanges(item, draft)
        if (!Object.keys(changes).length) {
            setErrors(["Nothing has changed."])
            return
        }
        setSaving(true)
        setErrors([])
        try {
            const result = await requestJson<JsonRecord>(
                `/api/work/${encodeRef(folder)}`,
                "PATCH",
                { changes, expected }
            )
            if (isStaleWrite(result)) {
                setStale(result.error)
                return
            }
            if (!result.ok) {
                setErrors([result.error || `Save failed (${result.status})`])
                return
            }
            onDirty(false)
            onSaved("Saved", result.data)
        } finally {
            setSaving(false)
        }
    }
    const context = { ...references, currentIdentifier: item.slug }
    const otherProject = (text: string) => otherProjectWarning(text, project.id)
    return (
        <div className={`editor-container${saving ? " saving" : ""}`}>
            <EditorHeader
                title={`Edit ${item.title}`}
                saving={saving}
                onSave={() => void save()}
                onCancel={onCancel}
            />
            <Errors errors={errors} />
            {stale && (
                <Callout.Root
                    className="conflict-banner"
                    color="amber"
                    role="alert"
                >
                    <Callout.Text>
                        <strong>Changed since this form loaded it</strong>
                        <Text as="p" size="2">
                            {stale}. Your draft is kept.
                        </Text>
                        <Flex gap="2" mt="2">
                            <Button size="1" variant="soft" onClick={onReload}>
                                Load the item again
                            </Button>
                        </Flex>
                    </Callout.Text>
                </Callout.Root>
            )}
            <RefusalContext.Provider value={refusals.report}>
                <div className="editor-fields">
                    <TextInput
                        label="Title"
                        value={draft.title}
                        onChange={(value) => set("title", value)}
                    />
                    <SelectInput
                        label="Priority"
                        value={draft.priority}
                        options={["", ...project.scales.priority]}
                        onChange={(value) => set("priority", value)}
                    />
                    <SelectInput
                        label="Effort"
                        value={draft.effort}
                        options={["", ...project.scales.size]}
                        onChange={(value) => set("effort", value)}
                    />
                    <SelectInput
                        label="Complexity"
                        value={draft.complexity}
                        options={["", ...project.scales.size]}
                        onChange={(value) => set("complexity", value)}
                    />
                    <ReferenceInput
                        label="Tags"
                        multiple
                        mode="refuse"
                        value={draft.tags}
                        options={project.tags.map((tag) => ({
                            identifier: tag,
                            displayName: tag,
                        }))}
                        onChange={(value) => set("tags", value)}
                    />
                    <ReferenceInput
                        label="Assignee"
                        value={draft.assignee}
                        options={referenceOptions("work-assignee", context)}
                        onChange={(value) => set("assignee", value)}
                    />
                    <ReferenceInput
                        label="Parent"
                        value={draft.parent}
                        mode="warn"
                        warning={otherProject}
                        source={suggestOtherItems}
                        options={referenceOptions("work-parent", context)}
                        onChange={(value) => set("parent", value)}
                    />
                    <ReferenceInput
                        label="Blocked by"
                        multiple
                        mode="warn"
                        warning={otherProject}
                        source={suggestOtherItems}
                        value={draft["blocked-by"]}
                        options={referenceOptions("work-blockers", {
                            ...context,
                            selected: draft["blocked-by"],
                        })}
                        onChange={(value) => set("blocked-by", value)}
                    />
                </div>
            </RefusalContext.Provider>
        </div>
    )
}

/** Add `blocks` links: one request per link, stopping at the first refusal,
 * so a refusal never leaves a link half made. An existing link is removed
 * from the other item's page, as the command line has no removal either. */
export function BlocksForm({
    project,
    item,
    folder,
    references,
    onSaved,
    onDirty,
}: {
    project: TProject
    item: WorkItem
    folder: string
    references: TReferenceContext
    onSaved: TSaved
    /** Whether links are chosen and not yet added. */
    onDirty: (dirty: boolean) => void
}) {
    const [targets, setTargetsState] = useState<string[]>([])
    const [busy, setBusy] = useState(false)
    const [report, setReport] = useState("")
    const refusals = useRefusals()
    const setTargets = (next: string[]) => {
        setTargetsState(next)
        onDirty(next.length > 0)
    }
    const add = async () => {
        if (refusals.pending.length) {
            setReport(refusals.pending.join(" "))
            return
        }
        setBusy(true)
        setReport("")
        const added: string[] = []
        try {
            for (const target of targets) {
                const result = await requestJson<JsonRecord>(
                    `/api/work/${encodeRef(folder)}/blocks`,
                    "POST",
                    { target, expected: false }
                )
                if (!result.ok) {
                    setReport(
                        `${added.length ? `Added ${added.join(", ")}. ` : ""}${target} was not added: ${result.error}`
                    )
                    setTargets(targets.slice(added.length))
                    if (added.length) onSaved(`Added ${added.join(", ")}`, null)
                    return
                }
                added.push(target)
            }
            setTargets([])
            onSaved(`Added ${added.join(", ")}`, null)
        } finally {
            setBusy(false)
        }
    }
    return (
        <section className="item-section" aria-label="Add blocks">
            <RefusalContext.Provider value={refusals.report}>
                <ReferenceInput
                    label="Blocks (add)"
                    multiple
                    mode="warn"
                    warning={(text) => otherProjectWarning(text, project.id)}
                    source={suggestOtherItems}
                    value={targets}
                    options={referenceOptions("work-blockers", {
                        ...references,
                        currentIdentifier: item.slug,
                        selected: [...item.blocks, ...targets],
                    })}
                    onChange={(value) => setTargets(value as string[])}
                />
            </RefusalContext.Provider>
            {report && (
                <Callout.Root color="red" role="alert">
                    <Callout.Text>{report}</Callout.Text>
                </Callout.Root>
            )}
            <Button
                size="1"
                type="button"
                disabled={busy || !targets.length}
                onClick={() => void add()}
            >
                Add
            </Button>
        </section>
    )
}

/** Add a comment. Comments are never edited or removed: they carry the
 * reasons for forced moves and discards. */
export function CommentBox({
    folder,
    onSaved,
    onDirty,
}: {
    folder: string
    onSaved: TSaved
    /** Whether comment text is typed and not yet added. */
    onDirty: (dirty: boolean) => void
}) {
    const [text, setTextState] = useState("")
    const setText = (next: string) => {
        setTextState(next)
        onDirty(next.trim().length > 0)
    }
    const [busy, setBusy] = useState(false)
    const [error, setError] = useState("")
    const add = async () => {
        setBusy(true)
        setError("")
        try {
            const result = await requestJson<JsonRecord>(
                `/api/work/${encodeRef(folder)}/comments`,
                "POST",
                { text }
            )
            if (!result.ok) {
                setError(result.error)
                return
            }
            setText("")
            onSaved("Comment added", result.data)
        } finally {
            setBusy(false)
        }
    }
    return (
        <Flex className="comment-box" direction="column" gap="2" mt="3">
            <TextArea
                aria-label="New comment"
                placeholder="Add a comment"
                value={text}
                onChange={(event) => setText(event.target.value)}
            />
            {error && <Text color="red">{error}</Text>}
            <Flex justify="end">
                <Button
                    size="1"
                    type="button"
                    disabled={busy || !text.trim()}
                    onClick={() => void add()}
                >
                    Add comment
                </Button>
            </Flex>
        </Flex>
    )
}

/** Which of priority, effort and complexity a new item may set here. */
function creatable(project: TProject, field: string): boolean {
    return (
        !isUnavailable(project.createFields) &&
        project.createFields.includes(field)
    )
}

/** A new work item: in this project with every property, or in a connected
 * project with only a title, request text and priority. */
export function NewItemForm({
    project,
    references,
    onCreated,
    onCancel,
    onDirty,
}: {
    project: TProject
    references: TReferenceContext
    /** The new item's folder in this project, or null when it was made
     * elsewhere; and the line to show. */
    onCreated: (folder: string | null, message: string) => void
    onCancel: () => void
    onDirty: (dirty: boolean) => void
}) {
    const [target, setTarget] = useState(project.id)
    const [title, setTitle] = useState("")
    const [requestText, setRequestText] = useState("")
    const [props, setProps] = useState<JsonRecord>({})
    const [atStart, setAtStart] = useState(true)
    const [saving, setSaving] = useState(false)
    const [errors, setErrors] = useState<string[]>([])
    const refusals = useRefusals()
    const here = target === project.id
    const backend = project.recordOwner === "backend"
    const set = (name: string, value: unknown) => {
        setProps((old) => ({ ...old, [name]: value }))
        onDirty(true)
    }
    const save = async () => {
        if (!title.trim()) {
            setErrors(["A title is required."])
            return
        }
        // Fields hidden for another project send nothing, so only what is
        // shown can hold back a save.
        if (here && refusals.pending.length) {
            setErrors(refusals.pending)
            return
        }
        setSaving(true)
        setErrors([])
        try {
            // Single values are sent trimmed, as the properties form does.
            const properties = Object.fromEntries(
                Object.entries(props)
                    .map(([name, value]): [string, unknown] => [
                        name,
                        typeof value === "string" ? value.trim() : value,
                    ])
                    .filter(
                        ([name, value]) =>
                            (here || name === "priority") &&
                            value !== "" &&
                            !(Array.isArray(value) && !value.length)
                    )
            )
            const body: JsonRecord = { title: title.trim(), properties }
            if (requestText.trim()) body.requestText = requestText
            if (!here) body.project = target
            if (here && project.inboxItems && !atStart)
                body.stage = project.inboxStage
            const result = await requestJson<{
                slug?: string
                ticket?: string
                warnings?: unknown
            }>("/api/work", "POST", body)
            if (!result.ok) {
                const ticket = (result.data as { ticket?: string } | null)
                    ?.ticket
                setErrors([
                    ticket
                        ? `${result.error} Ticket ${ticket} was made; adopt it from Tickets.`
                        : result.error || `Create failed (${result.status})`,
                ])
                return
            }
            onDirty(false)
            const made = result.data?.slug
            if (made && made.startsWith(`${project.id}/`))
                onCreated(made.slice(project.id.length + 1), `Created ${made}`)
            else
                onCreated(
                    null,
                    made
                        ? `Created ${made}`
                        : `Created ticket ${result.data?.ticket}`
                )
        } finally {
            setSaving(false)
        }
    }
    const targets = [project.id, ...project.projects.map((other) => other.id)]
    const describe = (id: string) => {
        if (id === project.id) return `${id} (this project)`
        const other = project.projects.find((entry) => entry.id === id)
        if (other?.upstream)
            return `${id} (upstream: creating there is refused)`
        if (other && !other.present) return `${id} (not on this machine)`
        return id
    }
    const context = { ...references, currentIdentifier: undefined }
    // In filesystem mode another project's item may be named, with a
    // warning; in Jira mode only this project's items with an item here.
    const crossProject = backend
        ? { mode: "refuse" as const }
        : {
              mode: "warn" as const,
              warning: (text: string) => otherProjectWarning(text, project.id),
              source: suggestOtherItems,
          }
    return (
        <div className={`editor-container${saving ? " saving" : ""}`}>
            <EditorHeader
                title="New item"
                saving={saving}
                onSave={() => void save()}
                onCancel={onCancel}
            />
            <Errors errors={errors} />
            <RefusalContext.Provider value={refusals.report}>
                <div className="editor-fields">
                    <SelectInput
                        label="Project"
                        value={target}
                        options={targets}
                        display={describe}
                        onChange={(value) => {
                            setTarget(value || project.id)
                            onDirty(true)
                        }}
                    />
                    <TextInput
                        label="Title"
                        value={title}
                        onChange={(value) => {
                            setTitle(value)
                            onDirty(true)
                        }}
                    />
                    {(!here || !backend || creatable(project, "priority")) && (
                        <SelectInput
                            label="Priority"
                            value={String(props.priority ?? "")}
                            options={["", ...project.scales.priority]}
                            onChange={(value) => set("priority", value)}
                        />
                    )}
                    {here && (
                        <>
                            {(!backend || creatable(project, "effort")) && (
                                <SelectInput
                                    label="Effort"
                                    value={String(props.effort ?? "")}
                                    options={["", ...project.scales.size]}
                                    onChange={(value) => set("effort", value)}
                                />
                            )}
                            {(!backend || creatable(project, "complexity")) && (
                                <SelectInput
                                    label="Complexity"
                                    value={String(props.complexity ?? "")}
                                    options={["", ...project.scales.size]}
                                    onChange={(value) =>
                                        set("complexity", value)
                                    }
                                />
                            )}
                            {backend && isUnavailable(project.createFields) && (
                                <Text color="gray" size="2">
                                    Priority, effort and complexity cannot be
                                    offered: {project.createFields.unavailable}
                                </Text>
                            )}
                            <ReferenceInput
                                label="Tags"
                                multiple
                                mode="refuse"
                                value={(props.tags as string[]) ?? []}
                                options={project.tags.map((tag) => ({
                                    identifier: tag,
                                    displayName: tag,
                                }))}
                                onChange={(value) => set("tags", value)}
                            />
                            <ReferenceInput
                                label="Assignee"
                                value={String(props.assignee ?? "")}
                                {...(backend
                                    ? {
                                          mode: "refuse" as const,
                                          source: suggestAssignees,
                                          showName: true,
                                      }
                                    : { mode: "allow" as const })}
                                options={
                                    backend
                                        ? []
                                        : referenceOptions(
                                              "work-assignee",
                                              context
                                          )
                                }
                                onChange={(value) => set("assignee", value)}
                            />
                            <ReferenceInput
                                label="Parent"
                                {...crossProject}
                                value={String(props.parent ?? "")}
                                options={referenceOptions(
                                    "work-parent",
                                    context
                                )}
                                onChange={(value) => set("parent", value)}
                            />
                            <ReferenceInput
                                label="Blocked by"
                                multiple
                                {...crossProject}
                                value={(props["blocked-by"] as string[]) ?? []}
                                options={referenceOptions("work-blockers", {
                                    ...context,
                                    selected:
                                        (props["blocked-by"] as string[]) ?? [],
                                })}
                                onChange={(value) => set("blocked-by", value)}
                            />
                            {project.inboxItems && (
                                <Text as="label" size="2">
                                    <Flex align="center" gap="2">
                                        <Checkbox
                                            checked={atStart}
                                            onCheckedChange={(checked) =>
                                                setAtStart(checked === true)
                                            }
                                        />
                                        Start at the first stage (
                                        {project.startStage}); unticked, it
                                        waits in {project.inboxStage}
                                    </Flex>
                                </Text>
                            )}
                        </>
                    )}
                </div>
            </RefusalContext.Provider>
            <div className="editor-section">Request</div>
            <MarkdownEditor
                value={requestText}
                onChange={(value) => {
                    setRequestText(value)
                    onDirty(true)
                }}
                placeholder="What is asked for"
            />
        </div>
    )
}

/** The backend's inbox: tickets with no item yet. Adopt makes the item and
 * opens it; a refused adopt says why and leaves the ticket listed. */
export function TicketsView({
    onAdopted,
}: {
    /** The new item's folder, the line to show, and, when the item was
     * made but the request stage's post hook failed, what failed. */
    onAdopted: (folder: string, message: string, problem: string | null) => void
}) {
    const [tickets, setTickets] = useState<TTicket[] | null>(null)
    const [error, setError] = useState("")
    const [refusals, setRefusals] = useState<Record<string, string>>({})
    const [busy, setBusy] = useState("")
    const [attempt, setAttempt] = useState(0)
    useEffect(() => {
        setError("")
        fetchJson<{ tickets: TTicket[] }>("/api/tickets")
            .then((found) => setTickets(found.tickets))
            .catch((failure: unknown) =>
                setError(
                    failure instanceof Error ? failure.message : String(failure)
                )
            )
    }, [attempt])
    const adopt = async (key: string) => {
        setBusy(key)
        try {
            const result = await requestJson<{
                slug: string
                problem?: string | null
            }>(`/api/tickets/${encodeRef(key)}/adopt`, "POST", {})
            if (!result.ok || !result.data?.slug) {
                setRefusals((old) => ({ ...old, [key]: result.error }))
                return
            }
            const slug = result.data.slug
            onAdopted(
                slug.slice(slug.indexOf("/") + 1),
                `Adopted ${key}`,
                result.data.problem ?? null
            )
        } finally {
            setBusy("")
        }
    }
    return (
        <section aria-label="Tickets">
            <Heading as="h2" size="5">
                Tickets
            </Heading>
            {error ? (
                <Callout.Root color="amber" role="status">
                    <Callout.Text>
                        The tickets could not be read: {error}{" "}
                        <Button
                            size="1"
                            variant="soft"
                            type="button"
                            onClick={() => setAttempt((count) => count + 1)}
                        >
                            Retry
                        </Button>
                    </Callout.Text>
                </Callout.Root>
            ) : tickets === null ? (
                <Text color="gray">Loading...</Text>
            ) : tickets.length === 0 ? (
                <Text color="gray">No tickets are waiting.</Text>
            ) : (
                tickets.map((ticket) => (
                    <div className="item-section" key={ticket.key}>
                        <Flex align="center" gap="2" justify="between">
                            <Text weight="bold">
                                <a
                                    href={ticket.url}
                                    target="_blank"
                                    rel="noreferrer"
                                >
                                    {ticket.key}
                                </a>{" "}
                                {ticket.summary}
                            </Text>
                            <Button
                                size="1"
                                type="button"
                                disabled={busy === ticket.key}
                                onClick={() => void adopt(ticket.key)}
                            >
                                Adopt
                            </Button>
                        </Flex>
                        <Text as="p" color="gray" size="1">
                            {[ticket.status, ticket.reporter, ticket.created]
                                .filter(Boolean)
                                .join(" · ")}
                        </Text>
                        {refusals[ticket.key] && (
                            <Text as="p" color="red" size="2">
                                {refusals[ticket.key]}
                            </Text>
                        )}
                    </div>
                ))
            )}
        </section>
    )
}
