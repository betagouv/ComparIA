<script lang="ts">
  import { goto } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import ovoidPictoSrc from '@gouvfr/dsfr/dist/artwork/background/ovoid.svg'
  import errorPictoSrc from '@gouvfr/dsfr/dist/artwork/pictograms/system/technical-error.svg'
  import { onDestroy, onMount } from 'svelte'

  const CHECK_INTERVAL_MS = 20_000

  onMount(() => {
    const interval = setInterval(async () => {
      try {
        const { enabled } = await api.request<{ enabled: boolean }>('/maintenance/status')
        if (!enabled) {
          goto(resolve('/'))
        }
      } catch (error) {
        console.error(`Maintenance status check failed: ${(error as Error).message}`)
      }
    }, CHECK_INTERVAL_MS)

    onDestroy(() => clearInterval(interval))
  })
</script>

<main class="flex min-h-screen items-center justify-center">
  <div class="fr-container">
    <div
      class="fr-my-7w fr-mt-md-12w fr-mb-md-10w fr-grid-row fr-grid-row--gutters fr-grid-row--middle fr-grid-row--center"
    >
      <div class="fr-py-0 fr-col-12 fr-col-md-6">
        <h1>{m['maintenance.title']()}</h1>
        <p class="fr-text--lead fr-mb-3w">{m['maintenance.desc']()}</p>
      </div>
      <div class="fr-col-12 fr-col-md-3 fr-col-offset-md-1 fr-px-6w fr-px-md-0 fr-py-0">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          class="fr-responsive-img fr-artwork"
          aria-hidden="true"
          width="160"
          height="200"
          viewBox="0 0 160 200"
        >
          <use class="fr-artwork-motif" href={ovoidPictoSrc + '#artwork-motif'}></use>
          <use class="fr-artwork-background" href={ovoidPictoSrc + '#artwork-background'}></use>
          <g transform="translate(40, 60)">
            <use class="fr-artwork-decorative" href={errorPictoSrc + '#artwork-decorative'}></use>
            <use class="fr-artwork-minor" href={errorPictoSrc + '#artwork-minor'}></use>
            <use class="fr-artwork-major" href={errorPictoSrc + '#artwork-major'}></use>
          </g>
        </svg>
      </div>
    </div>
  </div>
</main>
