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
    referenceOptions,
    type TReferenceField,
} from "../model/reference-search"
import type { Axis, CapabilityDetail, TaxonomyDetail } from "../model/types"
import { ReferenceInput } from "./reference-input"
import { LABELS } from "./route-utils"
import {
    Errors,
    Field,
    Fields,
    Markdown,
    MarkdownEditor,
    SelectInput,
    TextInput,
} from "./shared-components"
import type {
    TClientData as Data,
    TDetail as Detail,
    TDraft as Draft,
    TEditorSession as Editor,
} from "./ui-types"
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
}: {
    label: string
    options: readonly string[]
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
                            {term.name ?? term.slug}
                        </Heading>
                        <Text className="item-meta" color="gray" size="2">
                            {term.qualified ?? term.slug}
                        </Text>
                        <ModifiedAt value={term.modified} />
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
                    <ModifiedAt value={capability.modified} />
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
    data: Data
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
