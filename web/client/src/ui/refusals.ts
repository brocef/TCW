import { createContext, useCallback, useState } from "react"

/** Where a field reports text it holds but will not commit, so the form
 * around it can refuse to save rather than drop that text silently. Each
 * field reports under its own id, and "" when it holds none. */
type TReportRefusal = (field: string, refusal: string) => void
export const RefusalContext = createContext<TReportRefusal | null>(null)

/** For a form whose fields are `ReferenceInput`s: `report` goes in a
 * `RefusalContext.Provider` around the fields, and `pending` lists, per
 * field, the text it holds that it will not keep. A form refuses to save
 * while `pending` is not empty. */
export function useRefusals(): { report: TReportRefusal; pending: string[] } {
    const [held, setHeld] = useState<Record<string, string>>({})
    const report = useCallback<TReportRefusal>((field, refusal) => {
        setHeld((old) => {
            if ((old[field] ?? "") === refusal) return old
            const next = { ...old }
            if (refusal) next[field] = refusal
            else delete next[field]
            return next
        })
    }, [])
    return { report, pending: Object.values(held) }
}
