<script lang="ts">
  import { browser } from '$app/environment'
  import { goto } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import Toaster from '$components/Toaster.svelte'
  import { env } from '$env/dynamic/public'
  import { setAuthContext } from '$lib/auth.svelte'
  import { UnauthorizedError } from '$lib/fastapi-client'
  import { setI18nContext, setVotesContext } from '$lib/global.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { setModelsContext } from '$lib/models'
  import { setCohortContext } from '$lib/stores/cohortStore.svelte'
  import { createBrandThemeStyle } from '$lib/theme'
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
  // svelte-ignore state_referenced_locally
  const auth = setAuthContext(data.auth)
  let brandThemeStyle = $derived(createBrandThemeStyle(auth.config))

  if (env.PUBLIC_GIT_COMMIT) console.log(`Git commit: ${env.PUBLIC_GIT_COMMIT}`)

  onMount(() => {
    // Remove locale param to avoid locale changes override problems
    const params = new SvelteURLSearchParams(page.url.searchParams)
    if (params.get('locale')) {
      params.delete('locale')
      // eslint-disable-next-line svelte/no-navigation-without-resolve
      goto(`?${params}` + page.url.hash)
    }
  })

  // svelte-ignore state_referenced_locally
  setVotesContext(data.votes)
  // svelte-ignore state_referenced_locally
  setModelsContext(data.data)
  setI18nContext()
  setCohortContext()

  function handleError(_event: PromiseRejectionEvent) {
    // FIXME display error page on some error? display custom text in toast?
    useToast('Unexpected error', 10000, 'error')
    if (_event.reason instanceof UnauthorizedError) {
      goto(resolve('/login'))
    }
  }
</script>

<svelte:head>
  {@html brandThemeStyle}
</svelte:head>

<svelte:window on:unhandledrejection={handleError} />

<Toaster />

{@render children()}

<div id="tooltips"></div>
