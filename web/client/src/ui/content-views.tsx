import { useState } from "react"
import {
    Badge,
    Button,
    Callout,
    Card,
    Checkbox,
    Flex,
    Heading,
    IconButton,
    Popover,
    Select,
    Text,
} from "@radix-ui/themes"
import type { TSortDirection, TWorkSortKey } from "../model/tree"
import {
    referenceOptions,
    type TReferenceField,
} from "../model/reference-search"
import type {
    Axis,
    CapabilityDetail,
    JsonRecord,
    TaxonomyDetail,
    WorkDetail,
} from "../model/types"
import { ReferenceInput } from "./reference-input"
import { LABELS } from "./route-utils"
import {
    Errors,
    Field,
    Fields,
    Markdown,
    MarkdownEditor,
    Modal,
    SelectInput,
    TextInput,
} from "./shared-components"
import type {
    TClientData as Data,
    TDetail as Detail,
    TDraft as Draft,
    TEditorSession as Editor,
} from "./ui-types"

const WORK_STATUSES = ["backlog", "active", "completed"]
const CAPABILITY_FIELDS = [
    ["Status", ["", "Supported", "Partial", "Missing", "Blocked", "Omitted"]],
    ["Priority", ["", "P0", "P1", "P2", "P3"]],
    ["Lifecycle", ["", "Experimental", "Stable", "Deprecated"]],
    ["Feature", null],
    ["Subject", null],
    ["Roles", null],
    ["When", null],
    ["Gaps", null],
    ["Blocked by", null],
    ["Tracker", null],
    ["Planning doc", null],
    ["Superseded by", null],
] as const

export function FilterControls({
    axis,
    registeredTags,
    statusFilter,
    setStatusFilter,
    kindFilter,
    setKindFilter,
    tagFilter,
    setTagFilter,
    workSortKey,
    setWorkSortKey,
    workSortDirection,
    setWorkSortDirection,
}: {
    axis: Axis
    registeredTags: string[]
    statusFilter: Record<string, boolean>
    setStatusFilter: React.Dispatch<
        React.SetStateAction<Record<string, boolean>>
    >
    kindFilter: string[]
    setKindFilter: (value: string[]) => void
    tagFilter: string[]
    setTagFilter: (value: string[]) => void
    workSortKey: TWorkSortKey
    setWorkSortKey: (value: TWorkSortKey) => void
    workSortDirection: TSortDirection
    setWorkSortDirection: (value: TSortDirection) => void
}) {
    if (axis === "capabilities") return null
    const selectedStatuses = WORK_STATUSES.filter(
        (status) => statusFilter[status]
    )
    return (
        <Flex
            className="status-filters"
            role="group"
            aria-label="Filters"
            align="center"
            gap="2"
            wrap="wrap"
        >
            {axis === "work" && (
                <>
                    <FacetPopover
                        label="Status"
                        options={WORK_STATUSES}
                        value={selectedStatuses}
                        capitalize
                        onChange={(statuses) =>
                            setStatusFilter(
                                Object.fromEntries(
                                    WORK_STATUSES.map((status) => [
                                        status,
                                        statuses.includes(status),
                                    ])
                                )
                            )
                        }
                    />
                    <SortControl
                        sortKey={workSortKey}
                        direction={workSortDirection}
                        onSortKeyChange={setWorkSortKey}
                        onDirectionChange={setWorkSortDirection}
                    />
                </>
            )}
            <FacetPopover
                label={axis === "taxonomy" ? "Kind" : "Tags"}
                options={
                    axis === "taxonomy"
                        ? ["Feature", "Vocabulary"]
                        : registeredTags
                }
                value={axis === "taxonomy" ? kindFilter : tagFilter}
                onChange={axis === "taxonomy" ? setKindFilter : setTagFilter}
            />
        </Flex>
    )
}

function SortControl({
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
                    if (value === "name" || value === "modified")
                        onSortKeyChange(value)
                }}
            >
                <Select.Trigger aria-label="Sort work items" />
                <Select.Content>
                    <Select.Item value="name">Name</Select.Item>
                    <Select.Item value="modified">Modified</Select.Item>
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

function FacetPopover({
    label,
    options,
    value,
    onChange,
    capitalize = false,
}: {
    label: string
    options: readonly string[]
    value: string[]
    onChange: (value: string[]) => void
    capitalize?: boolean
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
                    {options.length ? (
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
                                    {capitalize
                                        ? option[0].toUpperCase() +
                                          option.slice(1)
                                        : option}
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

export function DetailView({
    axis,
    detail,
    onEdit,
    onResource,
    onOpen,
    onDeletePlanStage,
    onAction,
}: {
    axis: Axis
    detail: Detail
    onEdit: () => void
    onResource: (
        kind: "artifacts" | "sidecars" | "plan-stages",
        slug: string,
        name: string
    ) => void
    onOpen: (
        slug: string,
        name: string,
        kind?: "artifacts" | "plan-stages"
    ) => void
    onDeletePlanStage: (slug: string, name: string, revision?: string) => void
    onAction: (action: "start" | "complete" | "drop") => void
}) {
    if (axis === "work") {
        const payload = detail as WorkDetail
        const item = payload.item
        return (
            <>
                <div className="detail-head">
                    <div>
                        <Heading as="h2" size="5">
                            {item.title ?? item.slug}
                        </Heading>
                        <Text className="item-meta" color="gray" size="2">
                            {item.slug}
                        </Text>
                    </div>
                    <Flex className="detail-actions" align="center" gap="2">
                        <Badge>{item.status}</Badge>
                        <Button
                            className="edit-btn"
                            variant="soft"
                            type="button"
                            onClick={onEdit}
                        >
                            Edit
                        </Button>
                    </Flex>
                </div>
                <Flex className="action-buttons" gap="2" wrap="wrap">
                    {item.status === "backlog" && (
                        <>
                            <Button
                                className="action-btn start"
                                color="green"
                                variant="soft"
                                type="button"
                                onClick={() => onAction("start")}
                            >
                                Start
                            </Button>
                            <Button
                                className="action-btn drop"
                                color="red"
                                variant="soft"
                                type="button"
                                onClick={() => onAction("drop")}
                            >
                                Drop
                            </Button>
                        </>
                    )}
                    {item.status === "active" && (
                        <Button
                            className="action-btn complete"
                            color="green"
                            variant="soft"
                            type="button"
                            onClick={() => onAction("complete")}
                        >
                            Complete
                        </Button>
                    )}
                </Flex>
                <Fields>
                    <Field name="Priority" value={item.priority} />
                    <Field name="Effort" value={item.effort} />
                    <Field name="Complexity" value={item.complexity} />
                    <Field name="Tags" value={item.tags?.join(", ") || "-"} />
                    <Field name="Resolution" value={item.resolution} />
                    <Field
                        name="Blocked by"
                        value={
                            item.blocked_by
                                ?.map((b) => b.slug ?? b.external)
                                .join(", ") || "-"
                        }
                    />
                    {item.parent && <Field name="Parent" value={item.parent} />}
                    {item.initiative && (
                        <Field name="Initiative" value={item.initiative} />
                    )}
                </Fields>
                <div className="artifacts">
                    {payload.artifacts
                        .filter(
                            (resource) =>
                                resource.present &&
                                resource.name !== "initial-request"
                        )
                        .map((resource) => (
                            <Flex
                                className="artifact-group"
                                key={resource.name}
                            >
                                <Button
                                    className="artifact"
                                    variant="soft"
                                    type="button"
                                    onClick={() =>
                                        onOpen(item.slug, resource.name)
                                    }
                                >
                                    {resource.name}
                                </Button>
                                <IconButton
                                    className="artifact-edit"
                                    variant="ghost"
                                    type="button"
                                    aria-label={`Edit ${resource.name}`}
                                    onClick={() =>
                                        onResource(
                                            "artifacts",
                                            item.slug,
                                            resource.name
                                        )
                                    }
                                >
                                    ✎
                                </IconButton>
                            </Flex>
                        ))}
                </div>
                {payload.planStages?.length > 0 && (
                    <div className="plan-stages">
                        <Heading as="h3" size="3">
                            Plan stages
                        </Heading>
                        {payload.planStages.map((stage) => (
                            <Card className="plan-stage" key={stage.id}>
                                <div>
                                    <strong>{stage.title}</strong>
                                    <span className="item-meta">
                                        {" "}
                                        {stage.id}
                                    </span>
                                </div>
                                <div className="item-meta">
                                    Depends on:{" "}
                                    {stage.depends_on.length
                                        ? stage.depends_on.join(", ")
                                        : "none"}
                                    {stage.effort &&
                                        ` · effort ${stage.effort}`}
                                    {stage.complexity &&
                                        ` · complexity ${stage.complexity}`}
                                    {stage.priority != null &&
                                        ` · priority ${stage.priority}`}
                                    {stage.tags.length > 0 &&
                                        ` · ${stage.tags.join(", ")}`}
                                </div>
                                {payload.planStages.filter(
                                    (candidate) =>
                                        candidate.id !== stage.id &&
                                        JSON.stringify(candidate.depends_on) ===
                                            JSON.stringify(stage.depends_on)
                                ).length > 0 && (
                                    <div className="item-meta">
                                        Parallel with:{" "}
                                        {payload.planStages
                                            .filter(
                                                (candidate) =>
                                                    candidate.id !== stage.id &&
                                                    JSON.stringify(
                                                        candidate.depends_on
                                                    ) ===
                                                        JSON.stringify(
                                                            stage.depends_on
                                                        )
                                            )
                                            .map((candidate) => candidate.id)
                                            .join(", ")}
                                    </div>
                                )}
                                <Flex
                                    className="artifact-group"
                                    align="center"
                                    gap="2"
                                >
                                    <Text size="2">
                                        {stage.present
                                            ? "Document present"
                                            : "Document missing"}
                                    </Text>
                                    {stage.present && (
                                        <Button
                                            size="1"
                                            variant="soft"
                                            type="button"
                                            onClick={() =>
                                                onOpen(
                                                    item.slug,
                                                    stage.id,
                                                    "plan-stages"
                                                )
                                            }
                                        >
                                            Open
                                        </Button>
                                    )}
                                    <Button
                                        size="1"
                                        variant="soft"
                                        type="button"
                                        onClick={() =>
                                            onResource(
                                                "plan-stages",
                                                item.slug,
                                                stage.id
                                            )
                                        }
                                    >
                                        {stage.present ? "Edit" : "Create"}
                                    </Button>
                                    {stage.present && (
                                        <Button
                                            size="1"
                                            color="red"
                                            variant="soft"
                                            type="button"
                                            onClick={() =>
                                                onDeletePlanStage(
                                                    item.slug,
                                                    stage.id,
                                                    stage.revision
                                                )
                                            }
                                        >
                                            Delete
                                        </Button>
                                    )}
                                </Flex>
                            </Card>
                        ))}
                    </div>
                )}
                {payload.sidecars?.some((resource) => resource.present) && (
                    <div className="sidecars-section">
                        <Heading as="h3" size="3">
                            Sidecars
                        </Heading>
                        {payload.sidecars
                            .filter((resource) => resource.present)
                            .map((resource) => (
                                <Flex
                                    className="sidecar-item"
                                    key={resource.name}
                                    align="center"
                                    gap="2"
                                >
                                    <Text
                                        className="sidecar-name"
                                        color="gray"
                                        size="2"
                                    >
                                        {resource.name}
                                    </Text>
                                    <Button
                                        className="sidecar-edit-btn"
                                        size="1"
                                        variant="soft"
                                        type="button"
                                        onClick={() =>
                                            onResource(
                                                "sidecars",
                                                item.slug,
                                                resource.name
                                            )
                                        }
                                    >
                                        Edit
                                    </Button>
                                </Flex>
                            ))}
                    </div>
                )}
                <Markdown source={item.body ?? ""} resolveLinks />
            </>
        )
    }
    if (axis === "taxonomy") {
        const term = (detail as TaxonomyDetail).term
        return (
            <>
                <div className="detail-head">
                    <div>
                        <Heading as="h2" size="5">
                            {term.name ?? term.slug}
                        </Heading>
                        <Text className="item-meta" color="gray" size="2">
                            {term.qualified ?? term.slug}
                        </Text>
                    </div>
                    <Flex className="detail-actions" align="center" gap="2">
                        <Badge>{term.kind}</Badge>
                        <Button
                            className="edit-btn"
                            variant="soft"
                            type="button"
                            onClick={onEdit}
                        >
                            Edit
                        </Button>
                    </Flex>
                </div>
                <Fields>
                    <Field name="Kind" value={term.kind} />
                    <Field name="Origin" value={term.origin} />
                    <Field name="Parent" value={term.parent} />
                    <Field
                        name="Relates to"
                        value={term.relates_to?.join(", ") || "-"}
                    />
                    <Field
                        name="Vocabulary"
                        value={term.vocabulary?.join(", ") || "-"}
                    />
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
                        {capability.name ?? capability.path}
                    </Heading>
                    <Text className="item-meta" color="gray" size="2">
                        {capability.path}
                    </Text>
                </div>
                <Flex className="detail-actions" align="center" gap="2">
                    <Badge>{capability.status}</Badge>
                    <Button
                        className="edit-btn"
                        variant="soft"
                        type="button"
                        onClick={onEdit}
                    >
                        Edit
                    </Button>
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
            <Markdown source={capability.body ?? ""} resolveLinks />
        </>
    )
}

export function EditorView({
    editor,
    setDraft,
    saving,
    errors,
    conflict,
    registeredTags,
    data,
    onSave,
    onCancel,
    onRefreshConflict,
}: {
    editor: Editor
    setDraft: (key: string, value: unknown) => void
    saving: boolean
    errors: string[]
    conflict: unknown
    registeredTags: string[]
    data: Data
    onSave: () => void
    onCancel: () => void
    onRefreshConflict: () => void
}) {
    if (editor.mode === "resource")
        return (
            <div className={`editor-container${saving ? " saving" : ""}`}>
                <EditorHeader
                    title={`Edit ${editor.kind === "artifacts" ? "Artifact" : editor.kind === "sidecars" ? "Sidecar" : "Plan stage"}: ${editor.name}`}
                    saving={saving}
                    onSave={onSave}
                    onCancel={onCancel}
                />
                <Errors errors={errors} />
                {Boolean(conflict) && (
                    <Conflict
                        onRefresh={onRefreshConflict}
                        onDiscard={onCancel}
                    />
                )}
                <MarkdownEditor
                    value={editor.draft}
                    onChange={(value) => setDraft("draft", value)}
                />
            </div>
        )
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
                {editor.axis === "work" && (
                    <WorkFields
                        draft={draft}
                        setDraft={setDraft}
                        registeredTags={registeredTags}
                        data={data}
                        current={
                            editor.mode === "core" ? editor.ref : undefined
                        }
                    />
                )}
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
                        current={
                            editor.mode === "core" ? editor.ref : undefined
                        }
                    />
                )}
            </div>
            <div className="editor-section">Body</div>
            <MarkdownEditor
                value={String(draft.body ?? "")}
                onChange={(value) => setDraft("body", value)}
            />
        </div>
    )
}

function EditorHeader({
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

function Conflict({
    onRefresh,
    onDiscard,
}: {
    onRefresh: () => void
    onDiscard: () => void
}) {
    return (
        <Callout.Root className="conflict-banner" color="amber" role="alert">
            <Callout.Text>
                <strong>Stale write detected</strong>
                <Text as="p" size="2">
                    The server version changed. Your draft is preserved.
                </Text>
                <Flex gap="2" mt="2">
                    <Button size="1" variant="soft" onClick={onRefresh}>
                        Refresh from server
                    </Button>
                    <Button
                        size="1"
                        color="red"
                        variant="soft"
                        onClick={onDiscard}
                    >
                        Discard draft
                    </Button>
                </Flex>
            </Callout.Text>
        </Callout.Root>
    )
}

function optionsFor(
    field: TReferenceField,
    data: Data,
    current?: string,
    selected?: string[]
) {
    return referenceOptions(field, {
        ...data,
        currentIdentifier: current,
        selected,
    })
}

function WorkFields({
    draft,
    setDraft,
    registeredTags,
    data,
    current,
}: {
    draft: Draft
    setDraft: (key: string, value: unknown) => void
    registeredTags: string[]
    data: Data
    current?: string
}) {
    const tags = (draft.tags as string[] | undefined) ?? []
    return (
        <>
            <TextInput
                label="Title"
                value={String(draft.title ?? "")}
                onChange={(value) => setDraft("title", value)}
            />
            <TextInput
                label="Priority"
                type="number"
                value={String(draft.priority ?? "")}
                onChange={(value) => setDraft("priority", value)}
            />
            <SelectInput
                label="Effort"
                value={String(draft.effort ?? "")}
                options={["", "low", "medium", "high", "very-high"]}
                onChange={(value) => setDraft("effort", value)}
            />
            <SelectInput
                label="Complexity"
                value={String(draft.complexity ?? "")}
                options={["", "low", "medium", "high", "very-high"]}
                onChange={(value) => setDraft("complexity", value)}
            />
            <ReferenceInput
                label="Parent"
                value={String(draft.parent ?? "")}
                options={optionsFor("work-parent", data, current)}
                onChange={(value) => setDraft("parent", value)}
            />
            <ReferenceInput
                label="Initiative"
                value={String(draft.initiative ?? "")}
                options={optionsFor("work-initiative", data, current)}
                onChange={(value) => setDraft("initiative", value)}
            />
            <ReferenceInput
                label="Blockers"
                multiple
                value={(draft.blockers as string[] | undefined) ?? []}
                options={optionsFor(
                    "work-blockers",
                    data,
                    current,
                    (draft.blockers as string[] | undefined) ?? []
                )}
                onChange={(value) => setDraft("blockers", value)}
            />
            <div className="field-group">
                <Text color="gray" size="1" weight="bold">
                    Tags
                </Text>
                <Flex className="tag-checkboxes" gap="3" wrap="wrap">
                    {[...new Set([...registeredTags, ...tags])].map((tag) => (
                        <Text
                            as="label"
                            className={`tag-checkbox${registeredTags.includes(tag) ? "" : " tag-stale"}`}
                            key={tag}
                            size="2"
                        >
                            <Flex align="center" gap="1">
                                <Checkbox
                                    checked={tags.includes(tag)}
                                    onCheckedChange={(checked) =>
                                        setDraft(
                                            "tags",
                                            checked
                                                ? [...tags, tag]
                                                : tags.filter(
                                                      (item) => item !== tag
                                                  )
                                        )
                                    }
                                />{" "}
                                {tag}
                                {registeredTags.includes(tag)
                                    ? ""
                                    : " (unregistered)"}
                            </Flex>
                        </Text>
                    ))}
                </Flex>
            </div>
        </>
    )
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
                        value={String(draft.parent ?? "")}
                        options={optionsFor("taxonomy-parent", data, current)}
                        onChange={(value) => setDraft("parent", value)}
                    />
                </>
            )}
            {!creating && (
                <ReferenceInput
                    label="Relates to"
                    multiple
                    value={(draft.relates_to as string[] | undefined) ?? []}
                    options={optionsFor(
                        "taxonomy-relates",
                        data,
                        current,
                        (draft.relates_to as string[] | undefined) ?? []
                    )}
                    onChange={(value) => setDraft("relates_to", value)}
                />
            )}
            <ReferenceInput
                label="Vocabulary"
                multiple
                value={(draft.vocabulary as string[] | undefined) ?? []}
                options={optionsFor(
                    "taxonomy-vocabulary",
                    data,
                    current,
                    (draft.vocabulary as string[] | undefined) ?? []
                )}
                onChange={(value) => setDraft("vocabulary", value)}
            />
        </>
    )
}

function CapabilityFields({
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
    if (creating)
        return (
            <>
                <TextInput
                    label="Path"
                    value={String(draft.path ?? "")}
                    placeholder="e.g. web/editing"
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
                    options={[
                        "Supported",
                        "Partial",
                        "Missing",
                        "Blocked",
                        "Omitted",
                    ]}
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
        Roles: { field: "capability-roles", multiple: true },
        When: { field: "capability-when", multiple: true, negated: true },
        "Blocked by": { field: "capability-blocked-by" },
        "Planning doc": { field: "capability-planning-doc" },
        "Superseded by": { field: "capability-superseded-by" },
    }
    return (
        <>
            {CAPABILITY_FIELDS.map(([label, selectOptions]) => {
                if (selectOptions)
                    return (
                        <SelectInput
                            label={label}
                            value={String(draft[label] ?? "")}
                            options={selectOptions}
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
                        options={optionsFor(
                            config.field,
                            data,
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

export function StartModal({
    onClose,
    onStart,
    errors,
}: {
    onClose: () => void
    onStart: (force: boolean) => Promise<boolean>
    errors: string[]
}) {
    const [failed, setFailed] = useState(false)
    return (
        <Modal title="Start Work Item" onClose={onClose}>
            <Errors errors={errors} />
            {failed && (
                <Callout.Root color="amber">
                    <Callout.Text>
                        This item may have unresolved blockers. You can
                        force-start it.
                    </Callout.Text>
                </Callout.Root>
            )}
            <Flex className="modal-actions" gap="2" justify="end">
                <Button
                    variant="soft"
                    color="gray"
                    type="button"
                    onClick={onClose}
                >
                    Cancel
                </Button>
                <Button
                    type="button"
                    onClick={() =>
                        void onStart(failed).then((ok) => {
                            if (!ok) setFailed(true)
                        })
                    }
                >
                    {failed ? "Start (force)" : "Start"}
                </Button>
            </Flex>
        </Modal>
    )
}

export function CompleteModal({
    detail,
    onClose,
    onComplete,
    errors,
}: {
    detail: WorkDetail
    onClose: () => void
    onComplete: (options: JsonRecord) => Promise<boolean>
    errors: string[]
}) {
    const checklist = detail.dodChecklist?.length
        ? detail.dodChecklist
        : [
              "tests pass",
              "docs synced",
              "capabilities reconciled",
              "reviewed",
              "version offered",
          ]
    const [checked, setChecked] = useState<string[]>([])
    const [resolution, setResolution] = useState("")
    const [force, setForce] = useState(false)
    return (
        <Modal title="Complete Work Item" onClose={onClose}>
            <Errors errors={errors} />
            <Callout.Root className="reconciliation-reminder" color="blue">
                <Callout.Text>
                    <strong>Reconciliation reminder</strong>
                    <br />
                    Reconcile the capabilities ledger before completing.
                </Callout.Text>
            </Callout.Root>
            <SelectInput
                label="Resolution"
                value={resolution}
                options={["", "done", "wontfix", "duplicate", "superseded"]}
                onChange={setResolution}
            />
            <Heading as="h3" size="3">
                Definition of Done
            </Heading>
            <Flex className="dod-list" direction="column">
                {checklist.map((item) => (
                    <Text as="label" className="dod-item" key={item} size="2">
                        <Flex align="center" gap="2">
                            <Checkbox
                                checked={checked.includes(item)}
                                onCheckedChange={(next) =>
                                    setChecked(
                                        next
                                            ? [...checked, item]
                                            : checked.filter(
                                                  (value) => value !== item
                                              )
                                    )
                                }
                            />{" "}
                            {item}
                        </Flex>
                    </Text>
                ))}
            </Flex>
            {force && (
                <Callout.Root className="modal-error" color="red">
                    <Callout.Text>
                        Completion was blocked. You can retry while ignoring
                        blockers.
                    </Callout.Text>
                </Callout.Root>
            )}
            <Flex className="modal-actions" gap="2" justify="end">
                <Button
                    variant="soft"
                    color="gray"
                    type="button"
                    onClick={onClose}
                >
                    Cancel
                </Button>
                <Button
                    type="button"
                    disabled={
                        !resolution || checked.length !== checklist.length
                    }
                    onClick={() =>
                        void onComplete({
                            resolution,
                            dod_ack: checked,
                            force,
                        }).then((ok) => {
                            if (!ok) setForce(true)
                        })
                    }
                >
                    {force ? "Complete (ignore blockers)" : "Complete"}
                </Button>
            </Flex>
        </Modal>
    )
}
