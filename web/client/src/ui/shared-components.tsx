import {
    useEffect,
    useMemo,
    useRef,
    useState,
    type CSSProperties,
    type ReactNode,
} from "react"
import {
    Button,
    Callout,
    Card,
    Dialog,
    Flex,
    Heading,
    IconButton,
    Popover,
    RadioGroup,
    Select,
    Text,
    TextArea,
    TextField,
    Tooltip,
} from "@radix-ui/themes"
import { GearIcon } from "@radix-ui/react-icons"
import { marked } from "marked"
import { requestJson } from "../model/api"
import type {
    Axis,
    AxisItem,
    CapabilityItem,
    TaxonomyItem,
    TreeNode,
    WorkItem,
} from "../model/types"
import { ModifiedAt } from "./modified-at"
import { useThemePreference } from "../theme-context"
import { parseThemePreference } from "../theme-preference"
import { itemKey, itemTitle, pathFor } from "./route-utils"
import { beginResize } from "./ui-state"

export function Markdown({
    source,
    resolveLinks = false,
}: {
    source: string
    resolveLinks?: boolean
}) {
    const container = useRef<HTMLElement>(null)
    const html = useMemo(() => marked.parse(source || "") as string, [source])
    useEffect(() => {
        if (!resolveLinks || !container.current) return
        const anchors = [
            ...container.current.querySelectorAll<HTMLAnchorElement>(
                'a[href^="tcw://"]'
            ),
        ]
        if (!anchors.length) return
        const uris = anchors.map((anchor) => anchor.getAttribute("href")!)
        void requestJson<
            Record<string, { ok: boolean; axis?: Axis; key?: string }>
        >("/api/resolve", "POST", { uris }).then((result) => {
            for (const anchor of anchors) {
                const uri = anchor.getAttribute("href")!
                const resolved = result.data?.[uri]
                if (resolved?.ok && resolved.axis && resolved.key) {
                    anchor.href = pathFor(resolved.axis, resolved.key)
                    anchor.dataset.navAxis = resolved.axis
                    anchor.dataset.navKey = resolved.key
                } else {
                    anchor.classList.add("tcw-inert")
                    anchor.title = uri
                }
            }
        })
    }, [html, resolveLinks])
    return (
        <article
            ref={container}
            className="body"
            dangerouslySetInnerHTML={{ __html: html }}
        />
    )
}

export function Fields({ children }: { children: ReactNode }) {
    return <div className="fields">{children}</div>
}
export function Field({ name, value }: { name: string; value: unknown }) {
    return (
        <Card className="field" size="1">
            <Text as="div" color="gray" size="1">
                {name}
            </Text>
            <Text as="div" size="2">
                {String(value ?? "-")}
            </Text>
        </Card>
    )
}
export function Errors({ errors }: { errors: string[] }) {
    return errors.length ? (
        <Callout.Root color="red" role="alert">
            <Callout.Text>
                <strong>Validation errors</strong>
                <ul>
                    {errors.map((error) => (
                        <li key={error}>{error}</li>
                    ))}
                </ul>
            </Callout.Text>
        </Callout.Root>
    ) : null
}

export function Modal({
    title,
    children,
    onClose,
}: {
    title: string
    children: ReactNode
    onClose: () => void
}) {
    return (
        <Dialog.Root
            open
            onOpenChange={(open) => {
                if (!open) onClose()
            }}
        >
            <Dialog.Content className="modal-box" maxWidth="560px">
                <Flex justify="between" align="center" mb="3">
                    <Dialog.Title>{title}</Dialog.Title>
                    <Dialog.Close>
                        <IconButton
                            className="modal-dismiss"
                            variant="ghost"
                            type="button"
                            aria-label="Close"
                        >
                            ×
                        </IconButton>
                    </Dialog.Close>
                </Flex>
                {children}
            </Dialog.Content>
        </Dialog.Root>
    )
}

export function Tree<T extends AxisItem>({
    nodes,
    axis,
    selected,
    expanded,
    onToggle,
    onSelect,
    visible,
}: {
    nodes: Array<TreeNode<T>>
    axis: Axis
    selected: string | null
    expanded: Set<string>
    onToggle: (path: string) => void
    onSelect: (key: string) => void
    visible: (item: T) => boolean
}) {
    const renderNodes = (
        current: Array<TreeNode<T>>,
        depth: number
    ): ReactNode => (
        <div className="tree-children" role={depth === 0 ? "none" : "group"}>
            {current.map((node) => {
                const hasChildren = node.children.length > 0
                const isExpanded = expanded.has(node.path)
                const key = node.item ? itemKey(axis, node.item) : node.path
                return (
                    <div className="tree-node" key={node.path} role="none">
                        <div className="tree-row" role="none">
                            {Array.from({ length: depth }, (_, index) => (
                                <span className="tree-indent" key={index} />
                            ))}
                            {hasChildren ? (
                                <IconButton
                                    className="tree-toggle"
                                    variant="ghost"
                                    type="button"
                                    tabIndex={-1}
                                    aria-label={
                                        isExpanded
                                            ? `Collapse ${node.name}`
                                            : `Expand ${node.name}`
                                    }
                                    aria-expanded={isExpanded}
                                    onClick={() => onToggle(node.path)}
                                >
                                    {isExpanded ? "▾" : "▸"}
                                </IconButton>
                            ) : (
                                <span className="tree-spacer" />
                            )}
                            {node.item ? (
                                <div className="tree-item-content">
                                    <Button
                                        type="button"
                                        variant="soft"
                                        role="treeitem"
                                        aria-level={depth + 1}
                                        data-tree-path={node.path}
                                        aria-expanded={
                                            hasChildren ? isExpanded : undefined
                                        }
                                        aria-selected={selected === key}
                                        className={`item item-${axis}${axis === "work" ? ` st-${(node.item as WorkItem).status}` : ""}${selected === key ? " active" : ""}${visible(node.item) ? "" : " ancestor-dim"}`}
                                        onClick={() => onSelect(key)}
                                    >
                                        <div className="item-title">
                                            {itemTitle(axis, node.item)}
                                        </div>
                                        <div className="item-meta">
                                            <ItemMeta
                                                axis={axis}
                                                item={node.item}
                                            />
                                        </div>
                                    </Button>
                                    {axis === "work" && (
                                        <Tooltip
                                            content={
                                                <span className="copy-slug-tooltip">
                                                    Copy slug
                                                </span>
                                            }
                                        >
                                            <IconButton
                                                className="copy-slug"
                                                variant="ghost"
                                                type="button"
                                                aria-label="Copy slug to clipboard"
                                                onClick={() =>
                                                    void navigator.clipboard.writeText(
                                                        key
                                                    )
                                                }
                                            >
                                                ⎘
                                            </IconButton>
                                        </Tooltip>
                                    )}
                                </div>
                            ) : (
                                <Button
                                    className="tree-folder"
                                    variant="ghost"
                                    type="button"
                                    role="treeitem"
                                    aria-level={depth + 1}
                                    data-tree-path={node.path}
                                    aria-expanded={isExpanded}
                                    onClick={() => onToggle(node.path)}
                                >
                                    {node.name}
                                </Button>
                            )}
                        </div>
                        {hasChildren && isExpanded
                            ? renderNodes(node.children, depth + 1)
                            : null}
                    </div>
                )
            })}
        </div>
    )
    return renderNodes(nodes, 0)
}

export function ItemMeta({ axis, item }: { axis: Axis; item: AxisItem }) {
    if (axis === "work") {
        const work = item as WorkItem
        return (
            <div>
                <span className="work-status">{work.status}</span>
                {" · "}
                {[
                    work.effort && `effort ${work.effort}`,
                    work.complexity && `complexity ${work.complexity}`,
                    work.tags?.length && `tags ${work.tags.join(", ")}`,
                ]
                    .filter(Boolean)
                    .join(" · ")}
                <ModifiedAt value={work.modified} />
            </div>
        )
    }
    if (axis === "taxonomy") {
        const term = item as TaxonomyItem
        return (
            <div>
                <div>
                    {[term.kind, term.origin].filter(Boolean).join(" · ")}
                </div>
                <ModifiedAt value={term.modified} />
            </div>
        )
    }
    const capability = item as CapabilityItem
    return (
        <div>
            {[
                capability.status,
                capability.origin !== "local" && capability.origin,
            ]
                .filter(Boolean)
                .join(" · ")}
            <ModifiedAt value={capability.modified} />
        </div>
    )
}

export function MarkdownEditor({
    value,
    onChange,
    placeholder = "Write Markdown...",
}: {
    value: string
    onChange: (value: string) => void
    placeholder?: string
}) {
    const [fraction, setFraction] = useState(0.5)
    return (
        <div
            className="md-editor"
            style={{ "--md-split": `${fraction * 100}%` } as CSSProperties}
        >
            <TextArea
                className="md-input"
                aria-label="Markdown"
                value={value}
                placeholder={placeholder}
                onChange={(event) => onChange(event.target.value)}
            />
            <div
                className="md-resizer"
                role="separator"
                aria-orientation="vertical"
                aria-label="Resize Markdown editor"
                onPointerDown={(event) =>
                    beginResize(
                        event,
                        event.currentTarget.parentElement!,
                        0.2,
                        0.8,
                        setFraction
                    )
                }
            />
            <div className="md-preview">
                <Markdown source={value} />
            </div>
        </div>
    )
}

export function TextInput({
    label,
    value,
    onChange,
    type = "text",
    placeholder,
}: {
    label: string
    value: string | number
    onChange: (value: string) => void
    type?: "text" | "number"
    placeholder?: string
}) {
    return (
        <label className="field-group">
            <Text color="gray" size="1" weight="bold">
                {label}
            </Text>
            <TextField.Root
                className="field-input"
                aria-label={label}
                type={type}
                value={value}
                placeholder={placeholder}
                onChange={(event) => onChange(event.target.value)}
            />
        </label>
    )
}

export function SelectInput({
    label,
    value,
    options,
    onChange,
}: {
    label: string
    value: string
    options: readonly string[]
    onChange: (value: string) => void
}) {
    return (
        <label className="field-group">
            <Text color="gray" size="1" weight="bold">
                {label}
            </Text>
            <Select.Root
                value={value || "__unset__"}
                onValueChange={(next) =>
                    onChange(next === "__unset__" ? "" : next)
                }
            >
                <Select.Trigger aria-label={label} className="field-select" />
                <Select.Content>
                    {options.map((option) => (
                        <Select.Item
                            value={option || "__unset__"}
                            key={option || "__unset__"}
                        >
                            {option || "(unset)"}
                        </Select.Item>
                    ))}
                </Select.Content>
            </Select.Root>
        </label>
    )
}

export function SettingsControl() {
    const { preference, setPreference } = useThemePreference()
    return (
        <Popover.Root>
            <Tooltip content="Settings">
                <Popover.Trigger>
                    <IconButton aria-label="Settings" variant="soft">
                        <GearIcon />
                    </IconButton>
                </Popover.Trigger>
            </Tooltip>
            <Popover.Content align="end" width="220px">
                <Flex direction="column" gap="3">
                    <Heading as="h2" size="3">
                        Appearance
                    </Heading>
                    <RadioGroup.Root
                        value={preference}
                        onValueChange={(value) =>
                            setPreference(parseThemePreference(value))
                        }
                    >
                        <Flex direction="column" gap="2">
                            {(["light", "dark", "system"] as const).map(
                                (value) => (
                                    <Text as="label" key={value} size="2">
                                        <Flex align="center" gap="2">
                                            <RadioGroup.Item value={value} />
                                            {value[0].toUpperCase() +
                                                value.slice(1)}
                                        </Flex>
                                    </Text>
                                )
                            )}
                        </Flex>
                    </RadioGroup.Root>
                </Flex>
            </Popover.Content>
        </Popover.Root>
    )
}
