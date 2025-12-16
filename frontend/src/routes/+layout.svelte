<script lang="ts">
  import { browser } from '$app/environment'
  import { goto } from '$app/navigation'
  import { page } from '$app/state'
  import Toaster from '$components/Toaster.svelte'
  import { setI18nContext, setVotesContext } from '$lib/global.svelte'
  import { setModelsContext } from '$lib/models'
  import { onMount } from 'svelte'
  import { SvelteURLSearchParams } from 'svelte/reactivity'
  import 'uno.css'
  import '../css/app.css'

  if (browser) {
    // FIXME import only needed parts?
    // @ts-expect-error - DSFR module import
    import('@gouvfr/dsfr/dist/dsfr/dsfr.module.min.js')
  }

  let { children, data } = $props()

  onMount(() => {
    // Remove locale param to avoid locale changes override problems
    const params = new SvelteURLSearchParams(page.url.searchParams)
    params.delete('locale')
    goto(`?${params}`)
  })

  setVotesContext(data.votes)
  setModelsContext(data.data)
  setI18nContext()
</script>

<Toaster />

{@render children()}

<div id="tooltips"></div>
