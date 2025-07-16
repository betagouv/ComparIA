<script lang="ts">
  import { onMount } from 'svelte'

  let { data } = $props()

  onMount(async () => {
    // FIXME import only modal? Or create custom component
    // @ts-ignore - DSFR module import
    await import('@gouvfr/dsfr/dist/dsfr/dsfr.module.min.js')
  })
</script>

<h1>Bienvenue.</h1>
