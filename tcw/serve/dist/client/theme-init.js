;(() => {
    const key = "tcw.theme"
    let preference = "system"
    try {
        const stored = window.localStorage.getItem(key)
        if (stored === "light" || stored === "dark" || stored === "system") {
            preference = stored
        }
    } catch {
        // Inaccessible storage behaves like an unset preference.
    }
    const appearance =
        preference === "system"
            ? window.matchMedia("(prefers-color-scheme: dark)").matches
                ? "dark"
                : "light"
            : preference
    document.documentElement.classList.remove("light", "dark")
    document.documentElement.classList.add(appearance)
})()
