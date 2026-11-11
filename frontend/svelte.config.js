import adapter from '@sveltejs/adapter-node'
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte'

// The Instance path is chosen when the container starts, from one image: the
// image is built with this placeholder as base path and docker-entrypoint.sh
// replaces it in the built files. Unset, as in dev and tests, the app is served
// from the root. Dockerfile.front sets it, with the same default as the script.
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter(),
    // Absolute paths: `resolve` also answers in hooks, where relative ones (the
    // default) are meaningless, and the Instance path is read from it.
    paths: { base: process.env.INSTANCE_PATH_PLACEHOLDER || '', relative: false },
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
