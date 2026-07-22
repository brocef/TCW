import "@testing-library/jest-dom/vitest"

class TestResizeObserver implements ResizeObserver {
    disconnect() {}
    observe() {}
    unobserve() {}
}

globalThis.ResizeObserver = TestResizeObserver

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
