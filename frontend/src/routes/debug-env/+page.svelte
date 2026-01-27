<script lang="ts">
  import { env as publicEnv } from '$env/dynamic/public'
  import { browser, dev, building } from '$app/environment'

  // Fonction copiée de fastapi-client.ts pour test
  function getBackendUrl(): string {
    const ssr = !browser
    if (dev) {
      return 'http://localhost:8001 (dev mode)'
    } else if (ssr) {
      return publicEnv.PUBLIC_API_LOCAL_URL || publicEnv.PUBLIC_API_URL || 'http://localhost:8001 (SSR fallback)'
    } else {
      return window.location.origin || publicEnv.PUBLIC_API_URL || 'http://localhost:8001 (client fallback)'
    }
  }

  const envVars = {
    'browser': browser,
    'dev': dev,
    'building': building,
    'PUBLIC_API_URL': publicEnv.PUBLIC_API_URL || '(undefined)',
    'PUBLIC_API_LOCAL_URL': publicEnv.PUBLIC_API_LOCAL_URL || '(undefined)',
    'window.location.origin': browser ? window.location.origin : '(SSR)',
    'Computed Backend URL': getBackendUrl()
  }
</script>

<div style="padding: 2rem; font-family: monospace;">
  <h1>Debug Environment Variables</h1>
  <pre>{JSON.stringify(envVars, null, 2)}</pre>
</div>
