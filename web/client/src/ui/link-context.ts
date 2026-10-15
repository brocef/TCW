import { createContext } from "react"
import type { TReferenceOption } from "../model/reference-search"

/** The objects a `tcw://` link typed in a Markdown editor can name: every
 * entry of the three axes, which the page has loaded. */
export const LinkContext = createContext<TReferenceOption[]>([])
