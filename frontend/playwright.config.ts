import { defineConfig } from '@playwright/test'

// PLAYWRIGHT_BASE_URL points the suite at a server that is already up, which is
// how the accessibility sweep is meant to run: it needs the backend, so
// building a preview here would not be enough on its own.
const baseURL = process.env.PLAYWRIGHT_BASE_URL

export default defineConfig({
  testDir: 'e2e',
  use: { baseURL: baseURL ?? 'http://localhost:4173' },
  webServer: baseURL
    ? undefined
    : {
        command: 'npm run build && npm run preview',
        port: 4173
      }
})
