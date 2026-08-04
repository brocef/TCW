import { useEffect, useState } from "react"
import { Button, Flex, Tabs, Text } from "@radix-ui/themes"
import type { ResourceDetail, ResourceSummary, WorkItem } from "../model/types"
import { Markdown } from "./shared-components"

type TWorkDocumentName = "initial-request" | "spec" | "plan"

type TWorkDocument = {
    name: TWorkDocumentName
    label: string
}

type TWorkDocumentTabsProps = {
    item: WorkItem
    artifacts: ResourceSummary[]
    onEditInitialRequest: () => void
    onEditArtifact: (slug: string, name: "spec" | "plan") => void
    onReadArtifact: (
        slug: string,
        name: "spec" | "plan"
    ) => Promise<ResourceDetail>
}

type TArtifactState = {
    content?: string
    error?: string
    loading?: boolean
}

const WORK_DOCUMENTS: TWorkDocument[] = [
    { name: "initial-request", label: "Initial Request" },
    { name: "spec", label: "Spec" },
    { name: "plan", label: "Implementation Plan" },
]

export function WorkDocumentTabs({
    item,
    artifacts,
    onEditInitialRequest,
    onEditArtifact,
    onReadArtifact,
}: TWorkDocumentTabsProps) {
    const [selectedDocument, setSelectedDocument] =
        useState<TWorkDocumentName>("initial-request")
    const [artifactStates, setArtifactStates] = useState<
        Partial<Record<"spec" | "plan", TArtifactState>>
    >({})

    useEffect(() => {
        setSelectedDocument("initial-request")
        setArtifactStates({})
    }, [item.slug])

    const loadArtifact = (name: "spec" | "plan") => {
        const artifact = artifacts.find((candidate) => candidate.name === name)
        const state = artifactStates[name]
        if (
            !artifact?.present ||
            state?.content !== undefined ||
            state?.loading
        )
            return
        setArtifactStates((states) => ({
            ...states,
            [name]: { loading: true },
        }))
        void onReadArtifact(item.slug, name)
            .then((resource) => {
                setArtifactStates((states) => ({
                    ...states,
                    [name]: { content: resource.content },
                }))
            })
            .catch((error: unknown) => {
                setArtifactStates((states) => ({
                    ...states,
                    [name]: {
                        error:
                            error instanceof Error
                                ? error.message
                                : String(error),
                    },
                }))
            })
    }

    const selectedArtifact =
        selectedDocument === "initial-request"
            ? undefined
            : artifacts.find((artifact) => artifact.name === selectedDocument)
    const selectedState =
        selectedDocument === "initial-request"
            ? undefined
            : artifactStates[selectedDocument]

    const retry = () => {
        if (selectedDocument === "initial-request") return
        loadArtifact(selectedDocument)
    }

    return (
        <Tabs.Root
            className="work-document-tabs"
            value={selectedDocument}
            onValueChange={(value) => {
                if (
                    value === "initial-request" ||
                    value === "spec" ||
                    value === "plan"
                ) {
                    setSelectedDocument(value)
                    if (value !== "initial-request") loadArtifact(value)
                }
            }}
        >
            <Tabs.List aria-label="Work content">
                {WORK_DOCUMENTS.map((document) => (
                    <Tabs.Trigger
                        key={document.name}
                        value={document.name}
                        aria-label={document.label}
                    >
                        {document.label}
                    </Tabs.Trigger>
                ))}
            </Tabs.List>
            <div className="work-document-panel">
                {selectedDocument === "initial-request" ? (
                    <>
                        <Flex justify="end">
                            <Button
                                size="1"
                                variant="soft"
                                type="button"
                                onClick={onEditInitialRequest}
                            >
                                Edit Initial Request
                            </Button>
                        </Flex>
                        <Markdown source={item.body ?? ""} resolveLinks />
                    </>
                ) : !selectedArtifact?.present ? (
                    <Text color="gray">
                        {selectedDocument === "spec"
                            ? "Spec is not yet present."
                            : "Implementation Plan is not yet present."}
                    </Text>
                ) : selectedState?.error ? (
                    <Flex direction="column" align="start" gap="2">
                        <Text color="red">
                            Could not load this document: {selectedState.error}
                        </Text>
                        <Button
                            size="1"
                            variant="soft"
                            type="button"
                            onClick={retry}
                        >
                            Retry
                        </Button>
                    </Flex>
                ) : selectedState?.content === undefined ? (
                    <Text color="gray">Loading document...</Text>
                ) : (
                    <>
                        <Flex justify="end">
                            <Button
                                size="1"
                                variant="soft"
                                type="button"
                                onClick={() =>
                                    onEditArtifact(item.slug, selectedDocument)
                                }
                            >
                                Edit{" "}
                                {selectedDocument === "spec"
                                    ? "Spec"
                                    : "Implementation Plan"}
                            </Button>
                        </Flex>
                        <Markdown source={selectedState.content} resolveLinks />
                    </>
                )}
            </div>
        </Tabs.Root>
    )
}
