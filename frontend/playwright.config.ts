import { defineConfig } from '@playwright/test'

export default defineConfig({
  webServer: process.env.SKIP_WEBSERVER
    ? undefined
    : {
        command: 'npm run build && npm run preview',
        port: 4173
      },
  testDir: 'e2e'
})
