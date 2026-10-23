import { createContext } from "react"

/** The served project's ID: an entry whose `owner` is another project's is
 * inherited, and is routed by its whole full identifier (TCW-110 Design
 * 4.5). Empty until the project has loaded. */
export const ProjectIdContext = createContext("")
