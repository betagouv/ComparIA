<script lang="ts">
  import { browser } from '$app/environment'
  import Toaster from '$components/Toaster.svelte'
  import { setVotesContext } from '$lib/global.svelte'
  import { setModelsContext } from '$lib/models'
  import '../css/app.css'

  if (browser) {
    // FIXME import only needed parts?
    // @ts-ignore - DSFR module import
    import('@gouvfr/dsfr/dist/dsfr/dsfr.module.min.js')
  }

  let { children, data } = $props()

  setVotesContext(data.votes)
  setModelsContext(data.models)
</script>

<Toaster />

{@render children()}

<div id="tooltips"></div>
