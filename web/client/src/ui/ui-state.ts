import type { PointerEvent as ReactPointerEvent } from "react"
import type { Axis } from "../model/types"

export function beginResize(
    event: ReactPointerEvent<HTMLElement>,
    container: HTMLElement,
    minimum: number,
    maximum: number,
    onChange: (fraction: number) => void
) {
    event.preventDefault()
    const move = (pointer: PointerEvent) => {
        const bounds = container.getBoundingClientRect()
        onChange(
            Math.min(
                maximum,
                Math.max(
                    minimum,
                    (pointer.clientX - bounds.left) / bounds.width
                )
            )
        )
    }
    const stop = () => {
        window.removeEventListener("pointermove", move)
        window.removeEventListener("pointerup", stop)
    }
    window.addEventListener("pointermove", move)
    window.addEventListener("pointerup", stop)
}

export function loadExpanded(): Record<Axis, Set<string>> {
    const empty = (): Record<Axis, Set<string>> => ({
        work: new Set(),
        taxonomy: new Set(),
        capabilities: new Set(),
    })
    try {
        const stored = JSON.parse(
            localStorage.getItem("tcw.treeExpanded") ?? "{}"
        ) as Partial<Record<Axis, string[]>>
        return {
            work: new Set(stored.work),
            taxonomy: new Set(stored.taxonomy),
            capabilities: new Set(stored.capabilities),
        }
    } catch {
        return empty()
    }
}
