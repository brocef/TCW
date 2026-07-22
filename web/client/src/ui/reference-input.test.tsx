import { fireEvent, render, screen } from "@testing-library/react"
import { expect, test } from "vitest"
import { ReferenceInput } from "./reference-input"

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
