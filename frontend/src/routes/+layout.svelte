<script lang="ts">
  import Toaster from '$lib/components/Toaster.svelte'
  import { onMount } from 'svelte'
  import '../css/app.css'

  let { children } = $props()

  onMount(async () => {
    // FIXME import only needed parts?
    // @ts-ignore - DSFR module import
    await import('@gouvfr/dsfr/dist/dsfr/dsfr.module.min.js')
  })
</script>

<Toaster />

{@render children()}
