// vitest-setup-client.ts imports this at runtime, but it sits outside the
// include list in .svelte-kit/tsconfig.json, so the matcher types never
// reached svelte-check. Pull them in from a file that is included.
import '@testing-library/jest-dom/vitest'
