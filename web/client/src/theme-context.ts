import { createContext, useContext } from "react";
import type { TThemeAppearance, TThemePreference } from "./theme-preference";

export type TThemeContext = {
  appearance: TThemeAppearance;
  preference: TThemePreference;
  setPreference: (preference: TThemePreference) => void;
};

export const ThemeContext = createContext<TThemeContext | null>(null);

export function useThemePreference(): TThemeContext {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useThemePreference must be used within ThemeProvider");
  return context;
}
