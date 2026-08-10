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

// Svelte transitions drive themselves with the Web Animations API, which jsdom
// does not implement. This one finishes on the next tick, so a component that
// animates its way out is actually gone rather than stuck half removed.
Object.defineProperty(Element.prototype, 'animate', {
  writable: true,
  value: vi.fn().mockImplementation(() => {
    const animation = {
      cancel: vi.fn(),
      finish: vi.fn(),
      pause: vi.fn(),
      play: vi.fn(),
      startTime: 0,
      currentTime: 0,
      effect: null,
      onfinish: null as (() => void) | null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn()
    }
    setTimeout(() => animation.onfinish?.(), 0)
    return animation
  })
})

// add more mocks here if you need them
