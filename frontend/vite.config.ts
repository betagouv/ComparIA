import { paraglideVitePlugin } from '@inlang/paraglide-js'
import { sveltekit } from '@sveltejs/kit/vite'
import { svelteTesting } from '@testing-library/svelte/vite'
import UnoCSS from 'unocss/vite'
import { defineConfig } from 'vitest/config'
import { paraglideLocaleSplit } from './src/vite/paraglideLocaleSplit.js'

export default defineConfig({
  plugins: [
    UnoCSS(),
    sveltekit(),
    paraglideVitePlugin({
      project: './comparia.inlang',
      outdir: './src/lib/i18n',
      outputStructure: 'locale-modules',
      strategy: ['cookie', 'custom-url', 'baseLocale'],
      // Paraglide keeps the cookie 400 days by default, past the 13 months the
      // CNIL allows for a cookie set without consent.
      cookieMaxAge: 60 * 60 * 24 * 390
    }),
    paraglideLocaleSplit({ project: './comparia.inlang', outdir: './src/lib/i18n' })
  ],

  server: {
    fs: {
      allow: ['./static']
    }
  },
  test: {
    projects: [
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
  },
  build: {
    rollupOptions: {
      output: {
        codeSplitting: {
          groups: [
            {
              name: 'svelte',
              test: /node_modules[\\/]svelte|@sveltejs/
            }
          ]
        }
      }
    }
  }
})
