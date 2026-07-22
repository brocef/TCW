export type TThemePreference = "light" | "dark" | "system"
export type TThemeAppearance = "light" | "dark"

export const THEME_STORAGE_KEY = "tcw.theme"
export const DARK_SCHEME_QUERY = "(prefers-color-scheme: dark)"

export function parseThemePreference(value: string | null): TThemePreference {
    return value === "light" || value === "dark" || value === "system"
        ? value
        : "system"
}

export function readThemePreference(
    storage: Pick<Storage, "getItem"> | null = window.localStorage
): TThemePreference {
    try {
        return parseThemePreference(storage?.getItem(THEME_STORAGE_KEY) ?? null)
    } catch {
        return "system"
    }
}

export function resolveThemeAppearance(
    preference: TThemePreference,
    prefersDark: boolean
): TThemeAppearance {
    return preference === "system"
        ? prefersDark
            ? "dark"
            : "light"
        : preference
}

export function applyThemeAppearance(
    root: DOMTokenList,
    appearance: TThemeAppearance
): void {
    root.remove("light", "dark")
    root.add(appearance)
}
