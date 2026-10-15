import { useEffect, useState } from "react"
import { Button, Callout, Flex, Heading, Text } from "@radix-ui/themes"
import { encodeRef, fetchJson, isStaleWrite, requestJson } from "../model/api"
import {
    declarationField,
    referenceOptions,
    type TReferenceContext,
} from "../model/reference-search"
import type {
    JsonRecord,
    TDeclaration,
    TDeclarationLists,
} from "../model/types"
import { Conflict } from "./content-views"
import { ReferenceInput } from "./reference-input"
import { Errors, MarkdownEditor } from "./shared-components"
import type { TSaved } from "./work-forms"

type TAxis = "capabilities" | "taxonomy"
type TList = keyof TDeclarationLists

const AXES: Array<{ axis: TAxis; label: string }> = [
    { axis: "capabilities", label: "Capabilities" },
    { axis: "taxonomy", label: "Taxonomy" },
]
const LISTS: TList[] = ["new", "changed", "removed"]

const empty = (): TDeclarationLists => ({ new: [], changed: [], removed: [] })

/** The item's declaration file, `capabilities.yaml`, as six lists: what the
 * work adds, changes and removes in the capabilities ledger and the
 * taxonomy. A file the parser rejects opens as plain text, with the
 * parser's message, so it can be fixed; the form takes over once it parses.
 * In both, the page offers editing only when `editable`. */
export function DeclarationSection({
    folder,
    references,
    editable,
    onSaved,
    onDirty,
}: {
    folder: string
    references: TReferenceContext
    editable: boolean
    onSaved: TSaved
    onDirty: (dirty: boolean) => void
}) {
    const [found, setFound] = useState<TDeclaration | null>(null)
    const [error, setError] = useState("")
    const [editing, setEditing] = useState(false)
    const [attempt, setAttempt] = useState(0)
    const url = `/api/work/${encodeRef(folder)}/declaration`
    useEffect(() => {
        setError("")
        fetchJson<TDeclaration>(url)
            .then(setFound)
            .catch((failure: unknown) =>
                setError(
                    failure instanceof Error ? failure.message : String(failure)
                )
            )
    }, [url, attempt])
    const reload = () => setAttempt((count) => count + 1)
    const saved: TSaved = (message, response) => {
        setEditing(false)
        onDirty(false)
        reload()
        onSaved(message, response)
    }
    return (
        <section className="item-section" aria-label="Declaration">
            <Flex align="center" justify="between">
                <Heading as="h3" size="3">
                    Declared changes (capabilities.yaml)
                </Heading>
                {editable && found && !editing && (
                    <Button
                        size="1"
                        variant="soft"
                        type="button"
                        onClick={() => setEditing(true)}
                    >
                        {found.present ? "Edit" : "Create"}
                    </Button>
                )}
            </Flex>
            {error ? (
                <Text color="red">
                    {error}{" "}
                    <Button size="1" variant="soft" onClick={reload}>
                        Retry
                    </Button>
                </Text>
            ) : !found ? (
                <Text color="gray">Loading...</Text>
            ) : found.problem !== null ? (
                <PlainDeclaration
                    folder={folder}
                    found={found}
                    editing={editing}
                    onSaved={saved}
                    onCancel={() => {
                        setEditing(false)
                        onDirty(false)
                    }}
                    onDirty={onDirty}
                    onReload={reload}
                />
            ) : editing ? (
                <DeclarationForm
                    url={url}
                    found={found}
                    references={references}
                    onSaved={saved}
                    onCancel={() => {
                        setEditing(false)
                        onDirty(false)
                    }}
                    onDirty={onDirty}
                    onReload={reload}
                />
            ) : (
                <DeclarationLists found={found} />
            )}
        </section>
    )
}

function DeclarationLists({ found }: { found: TDeclaration }) {
    if (!found.present) return <Text color="gray">Nothing declared.</Text>
    return (
        <dl className="declaration-lists">
            {AXES.map(({ axis, label }) =>
                LISTS.map((list) => {
                    const values = found[axis]?.[list] ?? []
                    return values.length ? (
                        <div key={`${axis}-${list}`}>
                            <dt>
                                {label}: {list}
                            </dt>
                            <dd>{values.join(", ")}</dd>
                        </div>
                    ) : null
                })
            )}
        </dl>
    )
}

export function DeclarationForm({
    url,
    found,
    references,
    onSaved,
    onCancel,
    onDirty,
    onReload,
}: {
    url: string
    found: TDeclaration
    references: TReferenceContext
    onSaved: TSaved
    onCancel: () => void
    onDirty: (dirty: boolean) => void
    onReload: () => void
}) {
    const [draft, setDraft] = useState<Record<TAxis, TDeclarationLists>>({
        capabilities: { ...empty(), ...found.capabilities },
        taxonomy: { ...empty(), ...found.taxonomy },
    })
    const [saving, setSaving] = useState(false)
    const [errors, setErrors] = useState<string[]>([])
    const [stale, setStale] = useState(false)
    const save = async () => {
        setSaving(true)
        setErrors([])
        try {
            const result = await requestJson<JsonRecord>(url, "PUT", {
                ...draft,
                revision: found.revision,
            })
            if (isStaleWrite(result)) {
                setStale(true)
                return
            }
            if (!result.ok) {
                setErrors([result.error || `Save failed (${result.status})`])
                return
            }
            onSaved("capabilities.yaml saved", result.data)
        } finally {
            setSaving(false)
        }
    }
    return (
        <div className={saving ? "saving" : undefined}>
            <Text as="p" color="gray" size="2">
                Comments in this file are not kept when the form saves it.
            </Text>
            <Errors errors={errors} />
            {stale && <Conflict onRefresh={onReload} onDiscard={onCancel} />}
            {AXES.map(({ axis, label }) =>
                LISTS.map((list) => (
                    <ReferenceInput
                        key={`${axis}-${list}`}
                        label={`${label}: ${list}`}
                        multiple
                        mode={list === "new" ? "allow" : "refuse"}
                        value={draft[axis][list]}
                        options={referenceOptions(
                            declarationField(axis, list),
                            { ...references, selected: draft[axis][list] }
                        )}
                        onChange={(value) => {
                            setDraft((old) => ({
                                ...old,
                                [axis]: {
                                    ...old[axis],
                                    [list]: value as string[],
                                },
                            }))
                            onDirty(true)
                        }}
                    />
                ))
            )}
            <Flex gap="2" justify="end" mt="3">
                <Button
                    variant="soft"
                    color="gray"
                    type="button"
                    onClick={onCancel}
                >
                    Cancel
                </Button>
                <Button
                    type="button"
                    disabled={saving}
                    onClick={() => void save()}
                >
                    {saving ? "Saving..." : "Save"}
                </Button>
            </Flex>
        </div>
    )
}

/** A declaration file the parser rejects, as text, with its message. */
function PlainDeclaration({
    folder,
    found,
    editing,
    onSaved,
    onCancel,
    onDirty,
    onReload,
}: {
    folder: string
    found: TDeclaration
    editing: boolean
    onSaved: TSaved
    onCancel: () => void
    onDirty: (dirty: boolean) => void
    onReload: () => void
}) {
    const [draft, setDraft] = useState(found.content ?? "")
    const [errors, setErrors] = useState<string[]>([])
    const [stale, setStale] = useState(false)
    const save = async () => {
        const result = await requestJson<JsonRecord>(
            `/api/work/${encodeRef(folder)}/files/capabilities.yaml`,
            "PUT",
            { content: draft, revision: found.revision }
        )
        if (isStaleWrite(result)) {
            setStale(true)
            return
        }
        if (!result.ok) {
            setErrors([result.error || `Save failed (${result.status})`])
            return
        }
        onSaved("capabilities.yaml saved", result.data)
    }
    return (
        <>
            <Callout.Root color="amber" role="status">
                <Callout.Text>
                    This file cannot be read as lists: {found.problem}
                </Callout.Text>
            </Callout.Root>
            {editing ? (
                <>
                    <Errors errors={errors} />
                    {stale && (
                        <Conflict onRefresh={onReload} onDiscard={onCancel} />
                    )}
                    <MarkdownEditor
                        value={draft}
                        onChange={(value) => {
                            setDraft(value)
                            onDirty(true)
                        }}
                    />
                    <Flex gap="2" justify="end" mt="3">
                        <Button
                            variant="soft"
                            color="gray"
                            type="button"
                            onClick={onCancel}
                        >
                            Cancel
                        </Button>
                        <Button type="button" onClick={() => void save()}>
                            Save
                        </Button>
                    </Flex>
                </>
            ) : (
                <pre className="declaration-text">{found.content}</pre>
            )}
        </>
    )
}
