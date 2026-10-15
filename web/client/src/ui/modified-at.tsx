function formatted(value: string) {
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
    }).format(new Date(value))
}

export function ModifiedAt({ value }: { value?: string }) {
    return (
        <time className="modified-at" dateTime={value}>
            Modified at {value ? formatted(value) : "Unknown"}
        </time>
    )
}

/** A work item's date: when it was created. Work items carry no modified
 * time. */
export function CreatedAt({ value }: { value?: string }) {
    return (
        <time className="modified-at" dateTime={value || undefined}>
            Created {value ? formatted(value) : "at an unknown time"}
        </time>
    )
}
