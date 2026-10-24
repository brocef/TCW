import type { ReactNode } from "react"
import {
    Badge,
    Button,
    Callout,
    Card,
    Flex,
    Heading,
    Text,
} from "@radix-ui/themes"
import { isUnavailable } from "../model/api"
import { fullIdText } from "../model/identifier"
import {
    folderOf,
    isLocal,
    moveHint,
    personName,
    projectOf,
} from "../model/work"
import type {
    TComment,
    TFileContent,
    TProject,
    TUnavailable,
    WorkDetail,
    WorkItem,
} from "../model/types"
import { CreatedAt } from "./modified-at"
import { Field, Fields, Markdown } from "./shared-components"
import { WorkDocumentTabs, type TNewFileKind } from "./work-document-tabs"

/** A part the backend could not give: its message, and Retry. */
export function Unavailable({
    what,
    part,
    onRetry,
}: {
    what: string
    part: TUnavailable
    onRetry: () => void
}) {
    return (
        <Callout.Root color="amber" role="status" className="unavailable">
            <Callout.Text>
                {what} could not be read: {part.unavailable}{" "}
                <Button size="1" variant="soft" type="button" onClick={onRetry}>
                    Retry
                </Button>
            </Callout.Text>
        </Callout.Root>
    )
}

/** A work item named by its full identifier: a link that opens it when it is in this
 * project, and a labelled name that does not navigate when it is another
 * project's, which this page does not serve. */
export function SlugLink({
    slug,
    project,
}: {
    slug: string
    project: TProject
}) {
    const folder = folderOf(slug)
    if (isLocal(slug, project))
        return (
            <a
                href={`/work/${encodeURIComponent(folder)}`}
                data-nav-axis="work"
                data-nav-key={folder}
            >
                {folder}
            </a>
        )
    const owner = projectOf(slug) ?? ""
    return (
        <span
            className="tcw-other-project-name"
            title={`In project ${owner}; open it there`}
        >
            {folder} <Badge color="amber">{owner}</Badge>
        </span>
    )
}

function SlugList({ slugs, project }: { slugs: string[]; project: TProject }) {
    if (!slugs.length) return <>-</>
    return (
        <>
            {slugs.map((slug, index) => (
                <span key={slug}>
                    {index > 0 && ", "}
                    <SlugLink slug={slug} project={project} />
                </span>
            ))}
        </>
    )
}

function LinkField({ name, children }: { name: string; children: ReactNode }) {
    return (
        <Card className="field" size="1">
            <Text as="div" color="gray" size="1">
                {name}
            </Text>
            <Text as="div" size="2">
                {children}
            </Text>
        </Card>
    )
}

export function Properties({
    item,
    project,
    people,
}: {
    item: WorkItem
    project: TProject
    people: Record<string, string>
}) {
    return (
        <Fields>
            <Field name="Priority" value={item.priority ?? "none"} />
            <Field name="Effort" value={item.effort ?? "-"} />
            <Field name="Complexity" value={item.complexity ?? "-"} />
            <Field name="Tags" value={item.tags.join(", ") || "-"} />
            <Field
                name="Assignee"
                value={personName(item.assignee, people) || "-"}
            />
            <LinkField name="Parent">
                {item.parent ? (
                    <SlugLink slug={item.parent} project={project} />
                ) : (
                    "-"
                )}
            </LinkField>
            <LinkField name="Blocked by">
                <SlugList slugs={item["blocked-by"]} project={project} />
            </LinkField>
            <LinkField name="Blocks">
                <SlugList slugs={item.blocks} project={project} />
            </LinkField>
            <LinkField name="Children">
                <SlugList slugs={item.children} project={project} />
            </LinkField>
            {item.untracked.length > 0 && (
                <Field
                    name="Linked tickets with no item"
                    value={item.untracked.join(", ")}
                />
            )}
        </Fields>
    )
}

export function Comments({
    comments,
    limited,
    people,
    onRetry,
    children,
}: {
    comments: TComment[] | TUnavailable
    limited: boolean
    people: Record<string, string>
    onRetry: () => void
    /** The box that adds one, where comments can be added here. */
    children?: ReactNode
}) {
    return (
        <section className="item-section" aria-label="Comments">
            <Heading as="h3" size="3">
                Comments
            </Heading>
            {isUnavailable(comments) ? (
                <Unavailable
                    what="The comments"
                    part={comments}
                    onRetry={onRetry}
                />
            ) : (
                <>
                    {limited && (
                        <Text color="gray" size="2">
                            Showing the newest {comments.length}.
                        </Text>
                    )}
                    {comments.length === 0 && (
                        <Text color="gray" size="2">
                            No comments.
                        </Text>
                    )}
                    {comments.map((comment, index) => (
                        <Card
                            className="comment"
                            key={`${comment.at}-${index}`}
                        >
                            <Text as="div" color="gray" size="1">
                                {personName(comment.author, people)} ·{" "}
                                <time dateTime={comment.at}>
                                    {new Date(comment.at).toLocaleString()}
                                </time>
                            </Text>
                            <Markdown source={comment.text} resolveLinks />
                        </Card>
                    ))}
                </>
            )}
            {children}
        </section>
    )
}

export type TWorkPageEditing = {
    /** Opens the properties form. */
    onEditProperties?: () => void
    onEditFile?: (stage: string, path: string) => void
    onNewFile?: (stage: string, kind: TNewFileKind) => void
    /** Below the comments: the box that adds one. */
    commentBox?: ReactNode
    /** The declaration file's section. */
    declaration?: ReactNode
    /** The stage whose tab opens, when it is not the item's own: the stage
     * of the file the page was last left to edit, so that coming back from
     * the editor shows that file. */
    openStage?: string
}

/** A work item's page: title, folder, stage, properties, the request when the
 * backend keeps it, comments, and one tab per stage that keeps files. The
 * stage is shown, never changed: nothing here moves an item. */
export function WorkPage({
    project,
    detail,
    readFile,
    onRetry,
    editing = {},
}: {
    project: TProject
    detail: WorkDetail
    readFile: (path: string) => Promise<TFileContent>
    onRetry: () => void
    editing?: TWorkPageEditing
}) {
    const item = isUnavailable(detail.item) ? null : detail.item
    const slug =
        item?.["full-id"] ?? fullIdText(project.id, "work", detail.folder)
    return (
        <>
            <div className="detail-head">
                <div>
                    <Heading as="h2" size="5">
                        {item?.title ?? detail.folder}
                    </Heading>
                    <Text className="item-meta" color="gray" size="2">
                        {detail.folder}
                    </Text>
                    {item && <CreatedAt value={item.created} />}
                </div>
                <Flex className="detail-actions" align="center" gap="2">
                    {detail.link && (
                        <Button asChild variant="soft">
                            <a
                                href={detail.link.url}
                                target="_blank"
                                rel="noreferrer"
                            >
                                Open in {detail.link.label}
                            </a>
                        </Button>
                    )}
                    {item && editing.onEditProperties && (
                        <Button
                            className="edit-btn"
                            variant="soft"
                            type="button"
                            onClick={editing.onEditProperties}
                        >
                            Edit
                        </Button>
                    )}
                </Flex>
            </div>
            {isUnavailable(detail.item) ? (
                <Unavailable
                    what="The item's stage and properties"
                    part={detail.item}
                    onRetry={onRetry}
                />
            ) : (
                <>
                    <Text as="p" className="stage-line" size="2">
                        Stage: <strong>{item!.stage ?? "no stage"}</strong>.{" "}
                        <StageHint slug={slug} />
                    </Text>
                    <Properties
                        item={item!}
                        project={project}
                        people={detail.people}
                    />
                </>
            )}
            {detail.warnings.length > 0 && (
                <Callout.Root color="amber" role="status">
                    <Callout.Text>
                        Blocks and children leave out items that could not be
                        read: {detail.warnings.join(", ")}
                    </Callout.Text>
                </Callout.Root>
            )}
            {"requestText" in detail && (
                <section className="item-section" aria-label="Request">
                    <Heading as="h3" size="3">
                        Request
                    </Heading>
                    {isUnavailable(detail.requestText) ? (
                        <Unavailable
                            what="The request"
                            part={detail.requestText}
                            onRetry={onRetry}
                        />
                    ) : detail.requestText ? (
                        <Markdown source={detail.requestText} resolveLinks />
                    ) : (
                        <Text color="gray">No request text.</Text>
                    )}
                </section>
            )}
            <WorkDocumentTabs
                key={detail.folder}
                project={project}
                detail={detail}
                current={editing.openStage ?? item?.stage ?? null}
                readFile={readFile}
                onEditFile={editing.onEditFile}
                onNewFile={editing.onNewFile}
            />
            {editing.declaration}
            <Comments
                comments={detail.comments}
                limited={detail.commentsLimited}
                people={detail.people}
                onRetry={onRetry}
            >
                {editing.commentBox}
            </Comments>
        </>
    )
}

/** "Move it with `tcw work advance <slug>`.", the command in code type. */
function StageHint({ slug }: { slug: string }) {
    const [before, command, after] = moveHint(slug).split("`")
    return (
        <>
            {before}
            <code>{command}</code>
            {after}
        </>
    )
}
