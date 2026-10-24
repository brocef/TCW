import { useCallback, useContext } from "react"
import {
    Badge,
    Button,
    Callout,
    Checkbox,
    Flex,
    Heading,
    IconButton,
    Popover,
    Select,
    Text,
} from "@radix-ui/themes"
import type { TSortDirection, TWorkSortKey } from "../model/tree"
import { ModifiedAt } from "./modified-at"
import {
    pathSegments,
    referenceOptions,
    type TReferenceField,
} from "../model/reference-search"
import type {
    Axis,
    CapabilityDetail,
    CapabilityItem,
    TaxonomyDetail,
    TScopeProject,
    TScopeStatus,
} from "../model/types"
import { parseFullId, routeKey } from "../model/identifier"
import { ReferenceInput } from "./reference-input"
import { ProjectIdContext } from "./project-context"
import { LABELS, idPathOf, inherited, pathFor } from "./route-utils"
import {
    Errors,
    Field,
    Fields,
    Markdown,
    MarkdownEditor,
    OwnedBy,
    SelectInput,
    TextInput,
} from "./shared-components"
import type {
    TClientData as Data,
    TDetail as Detail,
    TDraft as Draft,
    TEditorSession as Editor,
} from "./ui-types"
/** The capability fields a form offers, in order. Status, priority and
 * lifecycle are fixed sets the project gives; the rest are references or
 * free text. */
const CAPABILITY_FIELDS = [
    ["Status", "status"],
    ["Priority", "priority"],
    ["Lifecycle", "lifecycle"],
    ["Feature", null],
    ["Subject", null],
    ["Roles", null],
    ["When", null],
    ["Gaps", null],
    ["Blocked by", null],
    ["Superseded by", null],
] as const

export function SortControl({
    sortKey,
    direction,
    onSortKeyChange,
    onDirectionChange,
}: {
    sortKey: TWorkSortKey
    direction: TSortDirection
    onSortKeyChange: (value: TWorkSortKey) => void
    onDirectionChange: (value: TSortDirection) => void
}) {
    const nextDirection = direction === "ascending" ? "descending" : "ascending"
    return (
        <Flex className="sort-control" align="center" gap="1">
            <Select.Root
                value={sortKey}
                onValueChange={(value) => {
                    if (
                        value === "name" ||
                        value === "created" ||
                        value === "priority"
                    )
                        onSortKeyChange(value)
                }}
            >
                <Select.Trigger aria-label="Sort work items" />
                <Select.Content>
                    <Select.Item value="name">Name</Select.Item>
                    <Select.Item value="created">Created</Select.Item>
                    <Select.Item value="priority">Priority</Select.Item>
                </Select.Content>
            </Select.Root>
            <IconButton
                type="button"
                size="1"
                variant="soft"
                aria-label={`Sort ${nextDirection}`}
                title={`Sort ${nextDirection}`}
                onClick={() => onDirectionChange(nextDirection)}
            >
                {direction === "ascending" ? "↑" : "↓"}
            </IconButton>
        </Flex>
    )
}

export function FacetPopover({
    label,
    options,
    value,
    onChange,
    display = (option: string) => option,
    unavailable,
}: {
    label: string
    options: readonly string[]
    /** Why the options could not be read, shown in their place. */
    unavailable?: string
    value: string[]
    onChange: (value: string[]) => void
    /** How an option reads: a stage as written, a person by name. */
    display?: (option: string) => string
}) {
    return (
        <Popover.Root>
            <Popover.Trigger>
                <Button size="1" variant="soft">
                    {label}
                    {value.length ? ` (${value.length})` : ""}
                </Button>
            </Popover.Trigger>
            <Popover.Content
                align="start"
                className="facet-panel"
                width="180px"
            >
                <Flex direction="column" gap="2">
                    {unavailable !== undefined ? (
                        <Text className="facet-empty" color="gray" size="1">
                            could not be read: {unavailable}
                        </Text>
                    ) : options.length ? (
                        options.map((option) => (
                            <Text
                                as="label"
                                className="facet-option"
                                key={option}
                                size="2"
                            >
                                <Flex align="center" gap="2">
                                    <Checkbox
                                        checked={value.includes(option)}
                                        onCheckedChange={(checked) =>
                                            onChange(
                                                checked
                                                    ? [...value, option]
                                                    : value.filter(
                                                          (selected) =>
                                                              selected !==
                                                              option
                                                      )
                                            )
                                        }
                                    />{" "}
                                    {display(option)}
                                </Flex>
                            </Text>
                        ))
                    ) : (
                        <Text className="facet-empty" color="gray" size="1">
                            none available
                        </Text>
                    )}
                </Flex>
            </Popover.Content>
        </Popover.Root>
    )
}

/** Another project's object is read-only here, whether this project
 * inherits it or not (TCW-113 Design 6.7): overriding an inherited one is a
 * deliberate act the command line offers. */
function EditOrOwned({ owner, onEdit }: { owner: string; onEdit: () => void }) {
    const projectId = useContext(ProjectIdContext)
    if (owner !== projectId) return <OwnedBy owner={owner} />
    return (
        <Button
            className="edit-btn"
            variant="soft"
            type="button"
            onClick={onEdit}
        >
            Edit
        </Button>
    )
}

/** What an entry overrides, as `show` prints it (TCW-112 Design 4.5), or
 * that its inherited content could not be read. */
function OverridesLine({
    record,
}: {
    record: { overrides?: string | null; partial?: boolean }
}) {
    if (record.partial)
        return (
            <Text as="div" className="item-meta" color="amber" size="2">
                partial: inherited content could not be read
            </Text>
        )
    if (!record.overrides) return null
    return (
        <Text as="div" className="item-meta" color="gray" size="2">
            overrides <code>{record.overrides}</code>
        </Text>
    )
}

export function DetailView({
    axis,
    detail,
    onEdit,
}: {
    axis: Exclude<Axis, "work">
    detail: Detail
    onEdit: () => void
}) {
    if (axis === "taxonomy") {
        const term = (detail as TaxonomyDetail).term
        return (
            <>
                <div className="detail-head">
                    <div>
                        <Heading as="h2" size="5">
                            {term.name ?? idPathOf(term)}
                        </Heading>
                        <Text className="item-meta" color="gray" size="2">
                            {term["full-id"]}
                        </Text>
                        <OverridesLine record={term} />
                        <ModifiedAt value={term.modified} />
                    </div>
                    <Flex className="detail-actions" align="center" gap="2">
                        <Badge>{term.kind}</Badge>
                        <EditOrOwned owner={term.owner} onEdit={onEdit} />
                    </Flex>
                </div>
                <Fields>
                    <Field name="Kind" value={term.kind} />
                    <Field name="Owner" value={term.owner} />
                    <Field name="Parent" value={term.parent} />
                    <Field
                        name="Relates to"
                        value={term.relates_to?.join(", ") || "-"}
                    />
                    {(term.kind === "Feature" ||
                        Boolean(term.vocabulary?.length)) && (
                        <Field
                            name="Vocabulary"
                            value={term.vocabulary?.join(", ") || "-"}
                        />
                    )}
                </Fields>
                <Markdown source={term.description ?? ""} resolveLinks />
            </>
        )
    }
    const capability = (detail as CapabilityDetail).capability
    return (
        <>
            <div className="detail-head">
                <div>
                    <Heading as="h2" size="5">
                        {capability.name ?? idPathOf(capability)}
                    </Heading>
                    <Text className="item-meta" color="gray" size="2">
                        {capability["full-id"]}
                    </Text>
                    <OverridesLine record={capability} />
                    <ModifiedAt value={capability.modified} />
                </div>
                <Flex className="detail-actions" align="center" gap="2">
                    <Badge>{capability.status}</Badge>
                    <EditOrOwned owner={capability.owner} onEdit={onEdit} />
                </Flex>
            </div>
            <Fields>
                {Object.entries(capability.fields ?? {}).map(
                    ([name, value]) => (
                        <Field
                            name={name}
                            value={
                                Array.isArray(value) ? value.join(", ") : value
                            }
                            key={name}
                        />
                    )
                )}
            </Fields>
            <StatusByProject
                capability={capability}
                projects={(detail as CapabilityDetail).projects}
            />
            <Markdown source={capability.body ?? ""} resolveLinks />
        </>
    )
}

/** Each status a capability path holds across the scope, with its
 * projects (TCW-113 Design 6.9): those that inherit it marked, each that
 * has an object of its own at the path linked to that object's page, and
 * the projects that could not be read. Shown only under `down` and `all`,
 * whose records carry `statuses`. */
function StatusByProject({
    capability,
    projects,
}: {
    capability: CapabilityItem
    projects?: TScopeProject[]
}) {
    const projectId = useContext(ProjectIdContext)
    if (!capability.statuses) return null
    const own = new Map<string, string>()
    for (const fullId of [
        capability["full-id"],
        ...(capability["overridden-by"] ?? []),
    ]) {
        const owner = parseFullId(fullId)?.project
        if (owner) own.set(owner, fullId)
    }
    const byStatus = new Map<string, TScopeStatus[]>()
    for (const entry of capability.statuses) {
        const name = entry.status ?? "(no status)"
        byStatus.set(name, [...(byStatus.get(name) ?? []), entry])
    }
    const unavailable = (projects ?? []).filter((p) => p.unavailable)
    return (
        <section className="status-by-project" aria-label="Status by project">
            <Heading as="h3" size="3">
                Status by project
            </Heading>
            <ul>
                {[...byStatus].map(([status, entries]) => (
                    <li key={status}>
                        {status}:{" "}
                        {entries.map((entry, index) => {
                            const fullId = own.get(entry.project)
                            const key = fullId && routeKey(fullId, projectId)
                            return (
                                <span key={entry.project}>
                                    {index > 0 && ", "}
                                    {key ? (
                                        <a
                                            href={pathFor("capabilities", key)}
                                            data-nav-axis="capabilities"
                                            data-nav-key={key}
                                        >
                                            {entry.project}
                                        </a>
                                    ) : (
                                        entry.project
                                    )}
                                    {entry.inherited && " (inherited)"}
                                </span>
                            )
                        })}
                    </li>
                ))}
                {unavailable.length > 0 && (
                    <li>
                        unavailable: {unavailable.map((p) => p.id).join(", ")}
                    </li>
                )}
            </ul>
        </section>
    )
}

export type TCapabilityScales = Record<
    "status" | "priority" | "lifecycle",
    string[]
>

export function EditorView({
    editor,
    setDraft,
    saving,
    errors,
    conflict,
    data,
    scales,
    onSave,
    onCancel,
    onRefreshConflict,
}: {
    editor: Editor
    setDraft: (key: string, value: unknown) => void
    saving: boolean
    errors: string[]
    conflict: unknown
    data: Data
    scales: TCapabilityScales
    onSave: () => void
    onCancel: () => void
    onRefreshConflict: () => void
}) {
    const draft = editor.draft
    return (
        <div className={`editor-container${saving ? " saving" : ""}`}>
            <EditorHeader
                title={`${editor.mode === "create" ? "Create" : "Edit"} ${LABELS[editor.axis]}`}
                saving={saving}
                onSave={onSave}
                onCancel={onCancel}
            />
            <Errors errors={errors} />
            {Boolean(conflict) && (
                <Conflict onRefresh={onRefreshConflict} onDiscard={onCancel} />
            )}
            <div className="editor-section">Fields</div>
            <div className="editor-fields">
                {editor.axis === "taxonomy" && (
                    <TaxonomyFields
                        draft={draft}
                        setDraft={setDraft}
                        creating={editor.mode === "create"}
                        data={data}
                        current={
                            editor.mode === "core" ? editor.ref : undefined
                        }
                    />
                )}
                {editor.axis === "capabilities" && (
                    <CapabilityFields
                        draft={draft}
                        setDraft={setDraft}
                        creating={editor.mode === "create"}
                        data={data}
                        scales={scales}
                        current={
                            editor.mode === "core" ? editor.ref : undefined
                        }
                    />
                )}
            </div>
            <div className="editor-section">Body</div>
            {editor.mode === "core" && editor.bodyNote && (
                <Text as="p" className="body-note" color="gray" size="2">
                    The body shown on the page also holds attached documents or
                    an inherited description, which this edit leaves unchanged.
                </Text>
            )}
            <MarkdownEditor
                value={String(draft.body ?? "")}
                onChange={(value) => setDraft("body", value)}
            />
        </div>
    )
}

export function EditorHeader({
    title,
    saving,
    onSave,
    onCancel,
}: {
    title: string
    saving: boolean
    onSave: () => void
    onCancel: () => void
}) {
    return (
        <Flex className="editor-header" justify="between" align="center">
            <Heading as="h2" className="editor-title" size="3">
                {title}
            </Heading>
            <Flex className="editor-actions" gap="2">
                <Button
                    variant="soft"
                    color="gray"
                    type="button"
                    onClick={onCancel}
                >
                    Cancel
                </Button>
                <Button type="button" disabled={saving} onClick={onSave}>
                    {saving ? "Saving..." : "Save"}
                </Button>
            </Flex>
        </Flex>
    )
}

export function Conflict({
    onRefresh,
    onDiscard,
}: {
    onRefresh: () => void
    onDiscard: () => void
}) {
    return (
        <Callout.Root className="conflict-banner" color="amber" role="alert">
            {/* Callout.Text is a <p>, so it holds only inline text; the
                buttons' Flex is a <div> and sits beside it. */}
            <Callout.Text>
                <strong>Stale write detected</strong>
                <Text as="span" size="2" style={{ display: "block" }}>
                    The server version changed. Your draft is preserved.
                </Text>
            </Callout.Text>
            <Flex gap="2" mt="2">
                <Button size="1" variant="soft" onClick={onRefresh}>
                    Refresh from server
                </Button>
                <Button size="1" color="red" variant="soft" onClick={onDiscard}>
                    Discard draft
                </Button>
            </Flex>
        </Callout.Root>
    )
}

function optionsFor(
    field: TReferenceField,
    data: Data,
    projectId: string,
    current?: string,
    selected?: string[]
) {
    return referenceOptions(field, {
        projectId,
        ...data,
        currentIdentifier: current,
        selected,
    })
}

function TaxonomyFields({
    draft,
    setDraft,
    creating,
    data,
    current,
}: {
    draft: Draft
    setDraft: (key: string, value: unknown) => void
    creating: boolean
    data: Data
    current?: string
}) {
    const projectId = useContext(ProjectIdContext)
    return (
        <>
            <TextInput
                label="Name"
                value={String(draft.name ?? "")}
                onChange={(value) => setDraft("name", value)}
            />
            <SelectInput
                label="Kind"
                value={String(draft.kind ?? "Vocabulary")}
                options={["Vocabulary", "Feature"]}
                onChange={(value) => setDraft("kind", value)}
            />
            {creating && (
                <>
                    <TextInput
                        label="Slug"
                        value={String(draft.slug ?? "")}
                        onChange={(value) => setDraft("slug", value)}
                    />
                    <ReferenceInput
                        label="Parent"
                        mode="refuse"
                        value={String(draft.parent ?? "")}
                        options={optionsFor(
                            "taxonomy-parent",
                            data,
                            projectId,
                            current
                        )}
                        onChange={(value) => setDraft("parent", value)}
                    />
                </>
            )}
            {!creating && (
                <ReferenceInput
                    label="Relates to"
                    multiple
                    mode="refuse"
                    value={(draft.relates_to as string[] | undefined) ?? []}
                    options={optionsFor(
                        "taxonomy-relates",
                        data,
                        projectId,
                        current,
                        (draft.relates_to as string[] | undefined) ?? []
                    )}
                    onChange={(value) => setDraft("relates_to", value)}
                />
            )}
            {/* A vocabulary is a Feature's: the terms it operates on. */}
            {draft.kind === "Feature" && (
                <ReferenceInput
                    label="Vocabulary"
                    multiple
                    mode="refuse"
                    value={(draft.vocabulary as string[] | undefined) ?? []}
                    options={optionsFor(
                        "taxonomy-vocabulary",
                        data,
                        projectId,
                        current,
                        (draft.vocabulary as string[] | undefined) ?? []
                    )}
                    onChange={(value) => setDraft("vocabulary", value)}
                />
            )}
        </>
    )
}

function CapabilityFields({
    draft,
    setDraft,
    creating,
    data,
    scales,
    current,
}: {
    draft: Draft
    setDraft: (key: string, value: unknown) => void
    creating: boolean
    data: Data
    scales: TCapabilityScales
    current?: string
}) {
    const projectId = useContext(ProjectIdContext)
    // One segment at a time, from the paths this project keeps; a new
    // segment is allowed.
    const pathSource = useCallback(
        async (text: string) =>
            pathSegments(
                data.capabilities
                    .filter((item) => !inherited(item, projectId))
                    .map(idPathOf),
                text
            ),
        [data.capabilities, projectId]
    )
    if (creating)
        return (
            <>
                <ReferenceInput
                    label="Path"
                    value={String(draft.path ?? "")}
                    options={[]}
                    source={pathSource}
                    onChange={(value) => setDraft("path", value)}
                />
                <TextInput
                    label="Name"
                    value={String(draft.name ?? "")}
                    onChange={(value) => setDraft("name", value)}
                />
                <SelectInput
                    label="Status"
                    value={String(draft.status ?? "Missing")}
                    options={scales.status}
                    onChange={(value) => setDraft("status", value)}
                />
            </>
        )
    const fields: Partial<
        Record<
            string,
            { field: TReferenceField; multiple?: boolean; negated?: boolean }
        >
    > = {
        Feature: { field: "capability-feature" },
        Subject: { field: "capability-subject", multiple: true },
        Roles: { field: "capability-roles", multiple: true, negated: true },
        When: { field: "capability-when", multiple: true, negated: true },
        "Blocked by": { field: "capability-blocked-by" },
        "Superseded by": { field: "capability-superseded-by" },
    }
    return (
        <>
            {CAPABILITY_FIELDS.map(([label, scale]) => {
                if (scale)
                    return (
                        <SelectInput
                            label={label}
                            value={String(draft[label] ?? "")}
                            options={["", ...scales[scale]]}
                            onChange={(value) => setDraft(label, value)}
                            key={label}
                        />
                    )
                const config = fields[label]
                if (!config)
                    return (
                        <TextInput
                            label={label}
                            value={String(draft[label] ?? "")}
                            onChange={(value) => setDraft(label, value)}
                            key={label}
                        />
                    )
                const fieldValue = config.multiple
                    ? Array.isArray(draft[label])
                        ? (draft[label] as string[])
                        : String(draft[label] ?? "")
                              .split(",")
                              .map((item) => item.trim())
                              .filter(Boolean)
                    : String(draft[label] ?? "")
                return (
                    <ReferenceInput
                        key={label}
                        label={label}
                        value={fieldValue}
                        multiple={config.multiple}
                        negated={config.negated}
                        mode="refuse"
                        options={optionsFor(
                            config.field,
                            data,
                            projectId,
                            current,
                            Array.isArray(fieldValue)
                                ? fieldValue.map((item) =>
                                      item.replace(/^!/, "")
                                  )
                                : undefined
                        )}
                        onChange={(value) => setDraft(label, value)}
                    />
                )
            })}
        </>
    )
}
