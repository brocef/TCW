export function ModifiedAt({ value }: { value?: string }) {
    const formatted = value
        ? new Intl.DateTimeFormat(undefined, {
              dateStyle: "medium",
              timeStyle: "short",
          }).format(new Date(value))
        : "Unknown"
    return (
        <time className="modified-at" dateTime={value}>
            Modified at {formatted}
        </time>
    )
}
