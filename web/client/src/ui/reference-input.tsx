import { useId, useMemo, useRef, useState, type KeyboardEvent } from "react"
import {
    Badge,
    Card,
    Flex,
    IconButton,
    Text,
    TextField,
} from "@radix-ui/themes"
import {
    highlightMatches,
    rankReferenceOptions,
    type TReferenceOption,
} from "../model/reference-search"

interface TReferenceInputProps {
    label: string
    options: TReferenceOption[]
    value: string | string[]
    multiple?: boolean
    negated?: boolean
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
    onChange,
}: TReferenceInputProps) {
    const id = useId()
    const values = useMemo(() => (Array.isArray(value) ? value : []), [value])
    const [query, setQuery] = useState(multiple ? "" : String(value))
    const [open, setOpen] = useState(false)
    const [active, setActive] = useState(-1)
    const input = useRef<HTMLInputElement>(null)
    const searchQuery =
        negated && query.startsWith("!") ? query.slice(1) : query
    const results = useMemo(
        () =>
            rankReferenceOptions(
                options.filter(
                    (candidate) => !values.includes(candidate.identifier)
                ),
                searchQuery
            ),
        [options, searchQuery, values]
    )

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
        setOpen(false)
        setActive(-1)
        input.current?.focus()
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
            if (active >= 0 && results[active]) {
                event.preventDefault()
                choose(results[active].identifier)
            } else if (multiple && query.trim()) {
                event.preventDefault()
                const raw = query.trim()
                if (!values.includes(raw)) onChange([...values, raw])
                setQuery("")
                setOpen(false)
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
                aria-activedescendant={
                    active >= 0 ? `${id}-option-${active}` : undefined
                }
                value={query}
                onFocus={() => setOpen(true)}
                onBlur={() => setOpen(false)}
                onChange={(event) => {
                    const next = event.target.value
                    const search =
                        negated && next.startsWith("!") ? next.slice(1) : next
                    setQuery(next)
                    setOpen(true)
                    setActive(
                        rankReferenceOptions(
                            options.filter(
                                (candidate) =>
                                    !values.includes(candidate.identifier)
                            ),
                            search
                        ).length
                            ? 0
                            : -1
                    )
                    if (!multiple) onChange(next)
                }}
                onKeyDown={onKeyDown}
            />
            {open && results.length > 0 && (
                <Card
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
                </Card>
            )}
        </div>
    )
}
