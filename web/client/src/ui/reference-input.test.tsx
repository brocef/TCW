import { useState } from "react"
import { act, fireEvent, render, screen } from "@testing-library/react"
import { expect, test, vi } from "vitest"
import { ReferenceInput } from "./reference-input"
import { RefusalContext, useRefusals } from "./refusals"

const options = [
    { displayName: "Useful editor", identifier: "web/use" },
    { displayName: "Online", identifier: "conditions/online" },
]

test("exposes combobox state and selects canonical identifiers by keyboard", () => {
    let value: string | string[] = ""
    const { rerender } = render(
        <ReferenceInput
            label="Feature"
            options={options}
            value={value}
            onChange={(next) => {
                value = next
            }}
        />
    )
    const input = screen.getByRole("combobox", { name: "Feature" })
    fireEvent.change(input, { target: { value: "use" } })
    expect(input).toHaveAttribute("aria-expanded", "true")
    expect(
        screen.getAllByText("use", { selector: "strong" }).length
    ).toBeGreaterThan(0)
    fireEvent.keyDown(input, { key: "ArrowDown" })
    fireEvent.keyDown(input, { key: "Enter" })
    expect(value).toBe("web/use")
    rerender(
        <ReferenceInput
            label="Feature"
            options={options}
            value={value}
            onChange={(next) => {
                value = next
            }}
        />
    )
})

test("supports pointer selection, duplicate-free raw text, and negated conditions", () => {
    let value: string | string[] = []
    const { rerender } = render(
        <ReferenceInput
            multiple
            negated
            label="When"
            options={options}
            value={value}
            onChange={(next) => {
                value = next
            }}
        />
    )
    const input = screen.getByRole("combobox", { name: "When" })
    fireEvent.change(input, { target: { value: "!on" } })
    fireEvent.pointerDown(screen.getByRole("option"))
    expect(value).toEqual(["!conditions/online"])
    rerender(
        <ReferenceInput
            multiple
            negated
            label="When"
            options={options}
            value={value}
            onChange={(next) => {
                value = next
            }}
        />
    )
    fireEvent.change(screen.getByRole("combobox"), {
        target: { value: "custom" },
    })
    fireEvent.keyDown(screen.getByRole("combobox"), { key: "Escape" })
    fireEvent.keyDown(screen.getByRole("combobox"), { key: "Enter" })
    expect(value).toEqual(["!conditions/online", "custom"])
})

test("renders results as a real dropdown surface", () => {
    render(
        <ReferenceInput
            label="Feature"
            options={options}
            value=""
            onChange={() => undefined}
        />
    )
    fireEvent.change(screen.getByRole("combobox"), {
        target: { value: "use" },
    })
    const listbox = screen.getByRole("listbox")
    expect(listbox).toHaveClass("reference-results")
    expect(listbox.tagName).toBe("DIV")
    expect(listbox).not.toHaveClass("rt-Card")
})

function Controlled(props: {
    multiple?: boolean
    negated?: boolean
    mode?: "refuse" | "warn" | "allow"
    warning?: (text: string) => string | null
    source?: (text: string) => Promise<typeof options>
    start?: string | string[]
    label?: string
    onValue?: (value: string | string[]) => void
}) {
    const [value, setValue] = useState<string | string[]>(
        props.start ?? (props.multiple ? [] : "")
    )
    return (
        <ReferenceInput
            label={props.label ?? "Field"}
            options={options}
            value={value}
            multiple={props.multiple}
            negated={props.negated}
            mode={props.mode}
            warning={props.warning}
            source={props.source}
            onChange={(next) => {
                setValue(next)
                props.onValue?.(next)
            }}
        />
    )
}

function typeAndCommit(text: string) {
    const input = screen.getByRole("combobox")
    fireEvent.change(input, { target: { value: text } })
    fireEvent.keyDown(input, { key: "Escape" })
    fireEvent.keyDown(input, { key: "Enter" })
}

test("a refusing list will not commit an unknown value, and says why", () => {
    const seen = vi.fn()
    render(<Controlled multiple mode="refuse" onValue={seen} />)
    typeAndCommit("nowhere")
    expect(seen).not.toHaveBeenCalled()
    expect(screen.getByRole("alert")).toHaveTextContent(
        "nowhere is not one of the suggestions, so it is not kept."
    )
    typeAndCommit("web/use")
    expect(seen).toHaveBeenLastCalledWith(["web/use"])
    expect(screen.queryByRole("alert")).toBeNull()
})

test("a refusing single field keeps its value, and the refused text with the reason", () => {
    const seen = vi.fn()
    render(<Controlled mode="refuse" start="web/use" onValue={seen} />)
    const input = screen.getByRole("combobox")
    fireEvent.change(input, { target: { value: "elsewhere" } })
    expect(seen).not.toHaveBeenCalled()
    fireEvent.blur(input)
    // The text stays where the person can see and fix it.
    expect(input).toHaveValue("elsewhere")
    expect(screen.getByRole("alert")).toHaveTextContent("elsewhere")
    expect(seen).not.toHaveBeenCalled()
    fireEvent.change(input, { target: { value: "" } })
    expect(seen).toHaveBeenLastCalledWith("")
})

test("Enter commits exactly what was typed; only an arrow key picks a suggestion", () => {
    const seen = vi.fn()
    render(<Controlled multiple onValue={seen} />)
    const input = screen.getByRole("combobox")
    fireEvent.change(input, { target: { value: "use" } })
    expect(screen.getByRole("listbox")).toBeInTheDocument()
    fireEvent.keyDown(input, { key: "Enter" })
    expect(seen).toHaveBeenLastCalledWith(["use"])
    fireEvent.change(input, { target: { value: "use" } })
    fireEvent.keyDown(input, { key: "ArrowDown" })
    fireEvent.keyDown(input, { key: "Enter" })
    expect(seen).toHaveBeenLastCalledWith(["use", "web/use"])
})

test("a warning field keeps another project's slug on Enter while suggestions are open", () => {
    const seen = vi.fn()
    const warning = (text: string) =>
        text.startsWith("other-project/") ? `${text} is not checked here` : null
    render(<Controlled multiple mode="warn" warning={warning} onValue={seen} />)
    const input = screen.getByRole("combobox")
    // "use" in the slug matches a suggestion, which must not replace it.
    fireEvent.change(input, { target: { value: "other-project/use" } })
    fireEvent.keyDown(input, { key: "Enter" })
    expect(seen).toHaveBeenLastCalledWith(["other-project/use"])
})

/** A form's fields inside the refusal context, with what it would refuse. */
function Form({ children }: { children: React.ReactNode }) {
    const refusals = useRefusals()
    return (
        <RefusalContext.Provider value={refusals.report}>
            {children}
            <output aria-label="pending">{refusals.pending.join(" | ")}</output>
        </RefusalContext.Provider>
    )
}

test("a field holding refused text reports it to the form until it is fixed", () => {
    render(
        <Form>
            <Controlled label="Parent" mode="refuse" />
            <Controlled label="Tags" mode="refuse" multiple />
        </Form>
    )
    const pending = screen.getByRole("status", { name: "pending" })
    expect(pending).toHaveTextContent("")
    const parent = screen.getByRole("combobox", { name: "Parent" })
    fireEvent.change(parent, { target: { value: "nowhere" } })
    fireEvent.blur(parent)
    expect(pending).toHaveTextContent(
        "Parent: nowhere is not one of the suggestions"
    )
    const tags = screen.getByRole("combobox", { name: "Tags" })
    fireEvent.change(tags, { target: { value: "nope" } })
    expect(pending).toHaveTextContent("Tags: nope")
    fireEvent.change(parent, { target: { value: "web/use" } })
    fireEvent.change(tags, { target: { value: "" } })
    expect(pending).toHaveTextContent("")
})

test("a field showing names commits the identifier and treats it as known", async () => {
    vi.useFakeTimers()
    try {
        const seen = vi.fn()
        const source = vi.fn(async (text: string) =>
            text === "ann"
                ? [{ identifier: "acc-123", displayName: "Ann Example" }]
                : []
        )
        function Named() {
            const [value, setValue] = useState<string | string[]>("")
            return (
                <ReferenceInput
                    label="Assignee"
                    mode="refuse"
                    showName
                    options={[]}
                    source={source}
                    value={value}
                    onChange={(next) => {
                        setValue(next)
                        seen(next)
                    }}
                />
            )
        }
        render(
            <Form>
                <Named />
            </Form>
        )
        const input = screen.getByRole("combobox", { name: "Assignee" })
        fireEvent.change(input, { target: { value: "ann" } })
        await act(async () => {
            await vi.advanceTimersByTimeAsync(200)
        })
        fireEvent.pointerDown(screen.getByRole("option", { name: /Ann/ }))
        expect(seen).toHaveBeenLastCalledWith("acc-123")
        expect(input).toHaveValue("Ann Example")
        await act(async () => {
            await vi.advanceTimersByTimeAsync(200)
        })
        fireEvent.blur(input)
        // The name is not searched again, and the value is not refused.
        expect(source).toHaveBeenCalledTimes(1)
        expect(screen.queryByRole("alert")).toBeNull()
        expect(
            screen.getByRole("status", { name: "pending" })
        ).toHaveTextContent("")
        expect(seen).toHaveBeenLastCalledWith("acc-123")
    } finally {
        vi.useRealTimers()
    }
})

test("a warning field keeps another project's slug with a warning", () => {
    const seen = vi.fn()
    const warning = (text: string) =>
        text.startsWith("other-project/") ? `${text} is not checked here` : null
    render(<Controlled multiple mode="warn" warning={warning} onValue={seen} />)
    typeAndCommit("other-project/2026-01-01-x")
    expect(seen).toHaveBeenLastCalledWith(["other-project/2026-01-01-x"])
    expect(
        screen.getByText("other-project/2026-01-01-x is not checked here")
    ).toBeInTheDocument()
    typeAndCommit("not a slug")
    expect(seen).toHaveBeenCalledTimes(1)
    expect(screen.getByRole("alert")).toHaveTextContent("not a slug")
})

test.each(["Roles", "When"])(
    "%s keeps a leading ! on a chosen value",
    (label) => {
        const seen = vi.fn()
        render(
            <Controlled
                label={label}
                multiple
                negated
                mode="refuse"
                onValue={seen}
            />
        )
        fireEvent.change(screen.getByRole("combobox"), {
            target: { value: "!online" },
        })
        fireEvent.pointerDown(screen.getByRole("option"))
        expect(seen).toHaveBeenLastCalledWith(["!conditions/online"])
        typeAndCommit("!web/use")
        expect(seen).toHaveBeenLastCalledWith([
            "!conditions/online",
            "!web/use",
        ])
    }
)

test("a server source adds suggestions for what is typed", async () => {
    const source = vi.fn(async (text: string) => [
        { identifier: `acc-${text}`, displayName: `Person ${text}` },
    ])
    render(<Controlled mode="refuse" source={source} />)
    fireEvent.change(screen.getByRole("combobox"), {
        target: { value: "ann" },
    })
    expect(
        await screen.findByRole("option", { name: /Person ann/ })
    ).toBeInTheDocument()
    expect(source).toHaveBeenCalledWith("ann")
})
