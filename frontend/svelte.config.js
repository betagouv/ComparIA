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
    csp: {
      // Nonces rather than hashes: the inline scripts in app.html carry runtime
      // values, so their hash is not known at build time. They read the nonce
      // from %sveltekit.nonce%. Nothing is prerendered, which nonce mode forbids.
      mode: 'nonce',
      directives: {
        'default-src': ['self'],
        'base-uri': ['none'],
        'object-src': ['none'],
        'frame-src': ['none'],
        'frame-ancestors': ['none'],
        'form-action': ['self'],
        'script-src': ['self'],
        // DSFR sets inline style attributes from its own JS, and the instance
        // brand colours are injected as an inline <style> whose content depends
        // on admin settings, so 'unsafe-inline' cannot be avoided here. Keeping
        // it also stops SvelteKit adding a nonce, which would void it.
        'style-src': ['self', 'unsafe-inline'],
        // https: covers the favicons that come back with web search results.
        'img-src': ['self', 'data:', 'https:'],
        'font-src': ['self', 'data:'],
        // The Matomo and API origins are appended at runtime in hooks.server.ts.
        'connect-src': ['self']
      }
    }
  }
}

export default config
