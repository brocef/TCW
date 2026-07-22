import { Theme } from "@radix-ui/themes";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ThemeContext, type TThemeContext } from "./theme-context";
import {
  applyThemeAppearance,
  DARK_SCHEME_QUERY,
  readThemePreference,
  resolveThemeAppearance,
  THEME_STORAGE_KEY,
  type TThemePreference,
} from "./theme-preference";

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [preference, setPreferenceState] = useState<TThemePreference>(() => readThemePreference());
  const [prefersDark, setPrefersDark] = useState(() => window.matchMedia(DARK_SCHEME_QUERY).matches);
  const appearance = resolveThemeAppearance(preference, prefersDark);

  useEffect(() => {
    applyThemeAppearance(document.documentElement.classList, appearance);
  }, [appearance]);

  useEffect(() => {
    const media = window.matchMedia(DARK_SCHEME_QUERY);
    const onMediaChange = (event: MediaQueryListEvent) => setPrefersDark(event.matches);
    const onStorage = (event: StorageEvent) => {
      if (event.key === THEME_STORAGE_KEY || event.key === null) {
        setPreferenceState(readThemePreference());
      }
    };
    media.addEventListener("change", onMediaChange);
    window.addEventListener("storage", onStorage);
    return () => {
      media.removeEventListener("change", onMediaChange);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  const value = useMemo<TThemeContext>(() => ({
    appearance,
    preference,
    setPreference: (nextPreference) => {
      setPreferenceState(nextPreference);
      try {
        window.localStorage.setItem(THEME_STORAGE_KEY, nextPreference);
      } catch {
        // The in-memory choice still applies when persistence is unavailable.
      }
    },
  }), [appearance, preference]);

  return <ThemeContext.Provider value={value}>
    <Theme
      accentColor="teal"
      appearance={appearance}
      grayColor="gray"
      panelBackground="solid"
      radius="small"
      scaling="90%"
    >
      {children}
    </Theme>
  </ThemeContext.Provider>;
}
