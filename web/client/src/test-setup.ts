import "@testing-library/jest-dom/vitest"

class TestResizeObserver implements ResizeObserver {
    disconnect() {}
    observe() {}
    unobserve() {}
}

globalThis.ResizeObserver = TestResizeObserver

// A test file may run in Node's own environment (`// @vitest-environment
// node`), which has no window.
if (typeof window !== "undefined") {
    Object.defineProperty(window, "matchMedia", {
        configurable: true,
        value: vi.fn().mockImplementation((query: string) => ({
            matches: false,
            media: query,
            onchange: null,
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            addListener: vi.fn(),
            removeListener: vi.fn(),
            dispatchEvent: vi.fn(),
        })),
    })
}
