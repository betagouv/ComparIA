import adapter from '@sveltejs/adapter-node'
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte'

const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter(),
    alias: {
      $css: './src/css',
      $components: './src/lib/components'
    },
    paths: {
      // Build-time only: one built image serves either a root-mounted or a
      // subpath-mounted deployment, never both. Defaults to root so current
      // production and the self-hosting chart (tickets 01-05) are unaffected.
      base: process.env.PUBLIC_BASE_PATH || ''
    }
  }
}

export default config
