import {
    applyThemeAppearance,
    parseThemePreference,
    readThemePreference,
    resolveThemeAppearance,
} from "./theme-preference"

test.each([
    [null, "system"],
    ["", "system"],
    ["invalid", "system"],
    ["light", "light"],
    ["dark", "dark"],
    ["system", "system"],
] as const)("parses %s as %s", (value, expected) => {
    expect(parseThemePreference(value)).toBe(expected)
})

test("defaults inaccessible storage to system", () => {
    expect(
        readThemePreference({
            getItem: () => {
                throw new Error("blocked")
            },
        })
    ).toBe("system")
})

test("resolves system while explicit preferences override it", () => {
    expect(resolveThemeAppearance("system", false)).toBe("light")
    expect(resolveThemeAppearance("system", true)).toBe("dark")
    expect(resolveThemeAppearance("light", true)).toBe("light")
    expect(resolveThemeAppearance("dark", false)).toBe("dark")
})

test("cleans the obsolete root appearance class", () => {
    const root = document.createElement("div")
    root.classList.add("light", "unrelated")
    applyThemeAppearance(root.classList, "dark")
    expect(root).toHaveClass("dark", "unrelated")
    expect(root).not.toHaveClass("light")
})
