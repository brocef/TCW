import { useEffect, useState } from "react"
import { Badge, Button, Flex, Tabs, Text } from "@radix-ui/themes"
import { stageLabel, stageVerdict } from "../model/work"
import type {
    TFileContent,
    TFileRef,
    TProject,
    TStageFiles,
    TStageRow,
    WorkDetail,
} from "../model/types"
import { Markdown } from "./shared-components"

export type TNewFileKind = "document" | "round" | "handoff"

type TWorkDocumentTabsProps = {
    project: TProject
    detail: WorkDetail
    /** The stage whose tab opens first: the item's own, when it has files. */
    current: string | null
    readFile: (path: string) => Promise<TFileContent>
    /** Absent when the page offers no editing. */
    onEditFile?: (stage: string, path: string) => void
    onNewFile?: (stage: string, kind: TNewFileKind) => void
}

/** One tab per enabled stage that keeps an artifact, in the table's order,
 * drawn from the project's stage rows: a document stage shows its document,
 * a rounds stage its rounds newest first with their verdicts, and either one
 * its handoffs. A stage the backend keeps says so, with the ticket's link. */
export function WorkDocumentTabs({
    project,
    detail,
    current,
    readFile,
    onEditFile,
    onNewFile,
}: TWorkDocumentTabsProps) {
    const rows = project.stages.filter((row) => row.artifact !== "none")
    const first =
        rows.find((row) => row.name === current)?.name ?? rows[0]?.name ?? ""
    const [selected, setSelected] = useState(first)
    useEffect(() => setSelected(first), [detail.folder]) // eslint-disable-line react-hooks/exhaustive-deps
    if (!rows.length) return null
    return (
        <Tabs.Root
            className="work-document-tabs"
            value={selected}
            onValueChange={setSelected}
        >
            <Tabs.List aria-label="Stage files">
                {rows.map((row) => (
                    <Tabs.Trigger
                        key={row.name}
                        value={row.name}
                        aria-label={stageLabel(row.name)}
                    >
                        {stageLabel(row.name)}
                    </Tabs.Trigger>
                ))}
            </Tabs.List>
            {rows.map((row) => (
                <Tabs.Content
                    className="work-document-panel"
                    key={row.name}
                    value={row.name}
                >
                    <StagePanel
                        row={row}
                        detail={detail}
                        readFile={readFile}
                        onEditFile={onEditFile}
                        onNewFile={onNewFile}
                    />
                </Tabs.Content>
            ))}
        </Tabs.Root>
    )
}

function StagePanel({
    row,
    detail,
    readFile,
    onEditFile,
    onNewFile,
}: {
    row: TStageRow
    detail: WorkDetail
    readFile: (path: string) => Promise<TFileContent>
    onEditFile?: (stage: string, path: string) => void
    onNewFile?: (stage: string, kind: TNewFileKind) => void
}) {
    if (row.external)
        return (
            <Flex direction="column" gap="2" align="start">
                <Text color="gray">
                    This project&apos;s backend keeps the {row.name} record.
                </Text>
                {detail.link && (
                    <a href={detail.link.url} target="_blank" rel="noreferrer">
                        Open in {detail.link.label}
                    </a>
                )}
            </Flex>
        )
    const files = detail.files.find((entry) => entry.stage === row.name)
    if (!files) return <Text color="gray">No files for this stage.</Text>
    return (
        <Flex direction="column" gap="3">
            {row.artifact === "document" ? (
                <DocumentPart
                    row={row}
                    files={files}
                    readFile={readFile}
                    onEditFile={onEditFile}
                    onNewFile={onNewFile}
                />
            ) : (
                <RoundsPart
                    row={row}
                    files={files}
                    verdict={stageVerdict(detail.verdicts, row.name)}
                    readFile={readFile}
                    onEditFile={onEditFile}
                    onNewFile={onNewFile}
                />
            )}
            <FileList
                title="Handoffs"
                entries={(files.handoffs ?? []).map((entry) => ({
                    ...entry,
                    label: entry.path.slice(entry.path.indexOf("/") + 1),
                }))}
                empty="No handoffs."
                stage={row.name}
                readFile={readFile}
                onEditFile={onEditFile}
                action={
                    onNewFile && (
                        <Button
                            size="1"
                            variant="soft"
                            type="button"
                            onClick={() => onNewFile(row.name, "handoff")}
                        >
                            New handoff
                        </Button>
                    )
                }
            />
        </Flex>
    )
}

function DocumentPart({
    row,
    files,
    readFile,
    onEditFile,
    onNewFile,
}: {
    row: TStageRow
    files: TStageFiles
    readFile: (path: string) => Promise<TFileContent>
    onEditFile?: (stage: string, path: string) => void
    onNewFile?: (stage: string, kind: TNewFileKind) => void
}) {
    const document = files.document
    if (!document?.present)
        return (
            <Flex align="center" gap="3">
                <Text color="gray">Not written.</Text>
                {onNewFile && (
                    <Button
                        size="1"
                        type="button"
                        onClick={() => onNewFile(row.name, "document")}
                    >
                        Create
                    </Button>
                )}
            </Flex>
        )
    return (
        <FileView
            file={document}
            readFile={readFile}
            onEdit={onEditFile && (() => onEditFile(row.name, document.path))}
        />
    )
}

function RoundsPart({
    row,
    files,
    verdict,
    readFile,
    onEditFile,
    onNewFile,
}: {
    row: TStageRow
    files: TStageFiles
    verdict: string | undefined
    readFile: (path: string) => Promise<TFileContent>
    onEditFile?: (stage: string, path: string) => void
    onNewFile?: (stage: string, kind: TNewFileKind) => void
}) {
    const rounds = files.rounds ?? []
    return (
        <Flex direction="column" gap="2">
            {row.verdict && (
                <Text size="2">
                    Current verdict: <strong>{verdict ?? "none"}</strong>
                </Text>
            )}
            <FileList
                title="Rounds"
                entries={rounds.map((round) => ({
                    ...round,
                    label: `Round ${round.number}`,
                    badge: row.verdict ? (round.verdict ?? "none") : undefined,
                }))}
                empty="No rounds yet."
                stage={row.name}
                readFile={readFile}
                onEditFile={onEditFile}
                open
                action={
                    onNewFile && (
                        <Button
                            size="1"
                            type="button"
                            onClick={() => onNewFile(row.name, "round")}
                        >
                            New round
                        </Button>
                    )
                }
            />
        </Flex>
    )
}

type TListedFile = TFileRef & { label: string; badge?: string }

/** Files newest first; choosing one shows it below the list. With `open`,
 * the newest is shown to begin with. */
function FileList({
    title,
    entries,
    empty,
    stage,
    readFile,
    onEditFile,
    action,
    open = false,
}: {
    title: string
    entries: TListedFile[]
    empty: string
    stage: string
    readFile: (path: string) => Promise<TFileContent>
    onEditFile?: (stage: string, path: string) => void
    action?: React.ReactNode
    open?: boolean
}) {
    const [chosen, setChosen] = useState<string | null>(
        open ? (entries[0]?.path ?? null) : null
    )
    const shown = entries.find((entry) => entry.path === chosen)
    return (
        <div className="file-list">
            <Flex align="center" justify="between" gap="2">
                <Text size="2" weight="bold">
                    {title}
                </Text>
                {action}
            </Flex>
            {entries.length === 0 ? (
                <Text color="gray" size="2">
                    {empty}
                </Text>
            ) : (
                <Flex direction="column">
                    {entries.map((entry) => (
                        <Flex className="file-row" key={entry.path}>
                            <Button
                                size="1"
                                variant={
                                    chosen === entry.path ? "solid" : "soft"
                                }
                                type="button"
                                aria-pressed={chosen === entry.path}
                                onClick={() =>
                                    setChosen(
                                        chosen === entry.path
                                            ? null
                                            : entry.path
                                    )
                                }
                            >
                                {entry.label}
                            </Button>
                            {entry.badge && <Badge>{entry.badge}</Badge>}
                        </Flex>
                    ))}
                </Flex>
            )}
            {shown && (
                <FileView
                    file={shown}
                    readFile={readFile}
                    onEdit={onEditFile && (() => onEditFile(stage, shown.path))}
                />
            )}
        </div>
    )
}

type TLoaded = { content?: string; error?: string }

/** One file's content, read when shown, with Retry when the read fails. */
export function FileView({
    file,
    readFile,
    onEdit,
}: {
    file: TFileRef
    readFile: (path: string) => Promise<TFileContent>
    onEdit?: () => void
}) {
    const [loaded, setLoaded] = useState<TLoaded>({})
    const [attempt, setAttempt] = useState(0)
    useEffect(() => {
        let stale = false
        setLoaded({})
        readFile(file.path)
            .then((found) => {
                if (!stale) setLoaded({ content: found.content })
            })
            .catch((error: unknown) => {
                if (!stale)
                    setLoaded({
                        error:
                            error instanceof Error
                                ? error.message
                                : String(error),
                    })
            })
        return () => {
            stale = true
        }
    }, [file.path, file.revision, attempt]) // eslint-disable-line react-hooks/exhaustive-deps
    if (loaded.error)
        return (
            <Flex direction="column" align="start" gap="2">
                <Text color="red">
                    Could not read {file.path}: {loaded.error}
                </Text>
                <Button
                    size="1"
                    variant="soft"
                    type="button"
                    onClick={() => setAttempt((count) => count + 1)}
                >
                    Retry
                </Button>
            </Flex>
        )
    if (loaded.content === undefined)
        return <Text color="gray">Loading {file.path}...</Text>
    return (
        <div className="file-view">
            <Flex justify="between" align="center">
                <Text className="file-name" color="gray" size="1">
                    {file.path}
                </Text>
                {onEdit && (
                    <Button
                        size="1"
                        variant="soft"
                        type="button"
                        onClick={onEdit}
                    >
                        Edit
                    </Button>
                )}
            </Flex>
            <Markdown source={loaded.content} resolveLinks />
        </div>
    )
}
