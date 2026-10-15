import {
    useEffect,
    useId,
    useMemo,
    useRef,
    useState,
    type KeyboardEvent,
} from "react"
import { Badge, Flex, IconButton, Text, TextField } from "@radix-ui/themes"
import {
    highlightMatches,
    rankReferenceOptions,
    type TReferenceOption,
} from "../model/reference-search"

/** What happens to text that matches no suggestion: `refuse` will not
 * commit it and says why; `warn` commits it when `warning` gives a reason
 * to keep it, shown under the field, and refuses it otherwise; `allow`
 * commits anything. */
export type TReferenceMode = "refuse" | "warn" | "allow"

interface TReferenceInputProps {
    label: string
    options: TReferenceOption[]
    value: string | string[]
    multiple?: boolean
    /** A leading `!` negates a value, and is kept on it. */
    negated?: boolean
    mode?: TReferenceMode
    /** In `warn` mode, the warning that lets an unknown value be kept. */
    warning?: (text: string) => string | null
    /** Suggestions the server computes from the typed text. */
    source?: (text: string) => Promise<TReferenceOption[]>
    onChange: (value: string | string[]) => void
}

function Highlight({ value, query }: { value: string; query: string }) {
    return (
        <>
            {highlightMatches(value, query).map((part, index) =>
                part.matched ? (
                    <strong key={index}>{part.text}</strong>
                ) : (
                    <span key={index}>{part.text}</span>
                )
            )}
        </>
    )
}

export function ReferenceInput({
    label,
    options,
    value,
    multiple = false,
    negated = false,
    mode = "allow",
    warning,
    source,
    onChange,
}: TReferenceInputProps) {
    const id = useId()
    const values = useMemo(() => (Array.isArray(value) ? value : []), [value])
    const [query, setQuery] = useState(multiple ? "" : String(value))
    const [open, setOpen] = useState(false)
    const [active, setActive] = useState(-1)
    const [remote, setRemote] = useState<TReferenceOption[]>([])
    const [refusal, setRefusal] = useState("")
    const input = useRef<HTMLInputElement>(null)
    const bare = (text: string) =>
        negated && text.startsWith("!") ? text.slice(1) : text
    const searchQuery = bare(query)

    useEffect(() => {
        if (!source || !searchQuery.trim()) {
            setRemote([])
            return
        }
        let stale = false
        const timer = window.setTimeout(() => {
            source(searchQuery.trim())
                .then((found) => {
                    if (!stale) setRemote(found)
                })
                .catch(() => {
                    if (!stale) setRemote([])
                })
        }, 150)
        return () => {
            stale = true
            window.clearTimeout(timer)
        }
    }, [source, searchQuery])

    const candidates = useMemo(() => {
        const seen = new Set<string>()
        return [...options, ...remote].filter((candidate) => {
            if (seen.has(candidate.identifier)) return false
            seen.add(candidate.identifier)
            return true
        })
    }, [options, remote])
    const results = useMemo(
        () =>
            rankReferenceOptions(
                candidates.filter(
                    (candidate) =>
                        !values.some(
                            (chosen) => bare(chosen) === candidate.identifier
                        )
                ),
                searchQuery
            ),
        [candidates, searchQuery, values] // eslint-disable-line react-hooks/exhaustive-deps
    )
    const known = (text: string) =>
        candidates.some((candidate) => candidate.identifier === bare(text))
    /** Why `text` cannot be committed, or "" when it can. */
    const refused = (text: string) => {
        if (!text || mode === "allow" || known(text)) return ""
        if (mode === "warn" && warning?.(bare(text))) return ""
        return `${text} is not one of the suggestions, so it is not kept.`
    }
    const warnings = (multiple ? values : value ? [String(value)] : [])
        .filter((chosen) => mode === "warn" && !known(chosen))
        .map((chosen) => warning?.(bare(chosen)))
        .filter((note): note is string => Boolean(note))

    const choose = (identifier: string) => {
        const selected =
            negated && query.startsWith("!") ? `!${identifier}` : identifier
        if (multiple) {
            onChange([...values, selected])
            setQuery("")
        } else {
            onChange(selected)
            setQuery(selected)
        }
        setRefusal("")
        setOpen(false)
        setActive(-1)
        input.current?.focus()
    }
    const commitTyped = () => {
        const raw = query.trim()
        if (!raw) return
        const why = refused(raw)
        if (why) {
            setRefusal(why)
            return
        }
        setRefusal("")
        if (multiple) {
            if (!values.includes(raw)) onChange([...values, raw])
            setQuery("")
        } else onChange(raw)
        setOpen(false)
    }
    const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
        if (event.key === "ArrowDown" && results.length) {
            event.preventDefault()
            setOpen(true)
            setActive((current) =>
                current < results.length - 1 ? current + 1 : 0
            )
        } else if (event.key === "ArrowUp" && results.length) {
            event.preventDefault()
            setOpen(true)
            setActive((current) =>
                current > 0 ? current - 1 : results.length - 1
            )
        } else if (event.key === "Escape") {
            setOpen(false)
            setActive(-1)
        } else if (event.key === "Enter") {
            if (open && active >= 0 && results[active]) {
                event.preventDefault()
                choose(results[active].identifier)
            } else if (query.trim()) {
                event.preventDefault()
                commitTyped()
            }
        }
    }
    return (
        <div className="field-group reference-field">
            <Text as="label" htmlFor={id} color="gray" size="1" weight="bold">
                {label}
            </Text>
            {multiple && (
                <Flex className="tag-list" gap="1" wrap="wrap">
                    {values.map((item) => (
                        <Badge className="tag" key={item}>
                            {item}
                            <IconButton
                                size="1"
                                variant="ghost"
                                type="button"
                                aria-label={`Remove ${item}`}
                                onClick={() =>
                                    onChange(
                                        values.filter(
                                            (candidate) => candidate !== item
                                        )
                                    )
                                }
                            >
                                ×
                            </IconButton>
                        </Badge>
                    ))}
                </Flex>
            )}
            <TextField.Root
                ref={input}
                id={id}
                className="field-input"
                role="combobox"
                aria-autocomplete="list"
                aria-expanded={open && results.length > 0}
                aria-controls={`${id}-listbox`}
                aria-invalid={refusal ? true : undefined}
                aria-activedescendant={
                    active >= 0 ? `${id}-option-${active}` : undefined
                }
                value={query}
                onFocus={() => setOpen(true)}
                onBlur={() => {
                    setOpen(false)
                    // A single value that would be refused is not kept: the
                    // field goes back to the value it holds, and says why.
                    if (
                        !multiple &&
                        mode !== "allow" &&
                        refused(query.trim())
                    ) {
                        setRefusal(refused(query.trim()))
                        setQuery(String(value))
                    }
                }}
                onChange={(event) => {
                    const next = event.target.value
                    setQuery(next)
                    setOpen(true)
                    setRefusal("")
                    setActive(
                        rankReferenceOptions(candidates, bare(next)).length
                            ? 0
                            : -1
                    )
                    // A single value is committed as typed only when it
                    // would be kept: empty, a suggestion, or allowed.
                    if (!multiple && !refused(next.trim()))
                        onChange(next.trim() ? next : "")
                }}
                onKeyDown={onKeyDown}
            />
            {refusal && (
                <Text
                    className="field-refusal"
                    color="red"
                    size="1"
                    role="alert"
                >
                    {refusal}
                </Text>
            )}
            {warnings.map((note) => (
                <Text
                    className="field-warning"
                    color="amber"
                    size="1"
                    key={note}
                >
                    {note}
                </Text>
            ))}
            {open && results.length > 0 && (
                <div
                    id={`${id}-listbox`}
                    className="reference-results"
                    role="listbox"
                >
                    {results.map((result, index) => (
                        <Flex
                            direction="column"
                            id={`${id}-option-${index}`}
                            role="option"
                            aria-selected={active === index}
                            className={`reference-option${active === index ? " active" : ""}`}
                            key={result.identifier}
                            onPointerDown={(event) => {
                                event.preventDefault()
                                choose(result.identifier)
                            }}
                        >
                            <Text size="2">
                                <Highlight
                                    value={result.displayName}
                                    query={searchQuery}
                                />
                            </Text>
                            <Text color="gray" size="1">
                                <Highlight
                                    value={result.identifier}
                                    query={searchQuery}
                                />
                            </Text>
                        </Flex>
                    ))}
                </div>
            )}
        </div>
    )
}
