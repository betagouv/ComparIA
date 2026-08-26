import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'

// required for svelte5 + jsdom as jsdom does not support matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  enumerable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn()
  }))
})

// jsdom has no layout engine and therefore does not provide ResizeObserver.
// Components may still create one during a page-level render; individual tests
// that need resize events can replace this no-op implementation with a driver.
Object.defineProperty(globalThis, 'ResizeObserver', {
  writable: true,
  configurable: true,
  value: class implements ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
})

// add more mocks here if you need them
