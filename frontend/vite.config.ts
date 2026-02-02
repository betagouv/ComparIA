import { paraglideVitePlugin } from '@inlang/paraglide-js'
import { sentrySvelteKit } from '@sentry/sveltekit'
import { sveltekit } from '@sveltejs/kit/vite'
import { svelteTesting } from '@testing-library/svelte/vite'
import UnoCSS from 'unocss/vite'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [
    sentrySvelteKit({
      sourceMapsUploadOptions: {
        org: process.env.SENTRY_ORG,
        project: process.env.SENTRY_PROJECT
      }
    }),
    UnoCSS(),
    sveltekit(),
    paraglideVitePlugin({
      project: './comparia.inlang',
      outdir: './src/lib/i18n',
      strategy: ['cookie', 'custom-url', 'baseLocale']
    })
  ],

  server: {
    fs: {
      allow: ['./static']
    }
  },
  test: {
    workspace: [
      {
        extends: './vite.config.ts',
        plugins: [svelteTesting()],
        test: {
          name: 'client',
          environment: 'jsdom',
          clearMocks: true,
          include: ['src/**/*.svelte.{test,spec}.{js,ts}'],
          exclude: ['src/lib/server/**'],
          setupFiles: ['./vitest-setup-client.ts']
        }
      },
      {
        extends: './vite.config.ts',
        test: {
          name: 'server',
          environment: 'node',
          include: ['src/**/*.{test,spec}.{js,ts}'],
          exclude: ['src/**/*.svelte.{test,spec}.{js,ts}']
        }
      }
    ]
  }
})
