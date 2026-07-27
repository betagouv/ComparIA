<script lang="ts">
  import LegalDocument from '$components/LegalDocument.svelte'
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'

  let { data } = $props()
</script>

<SeoHead title={m['seo.titles.modalites']()} />

<main class="py-10 lg:py-15">
  <div class="fr-container">
    <h1 id="modalites-d-utilisation">{m['general.tos.title']()}</h1>

    {#if data.terms}
      <LegalDocument
        version={data.terms.version}
        effectiveAt={data.terms.effective_at}
        content={data.terms.content}
        locale={data.terms.locale}
      />
    {:else}
      <p class="fr-alert fr-alert--error" role="alert">{m['general.document.unavailable']()}</p>
    {/if}
  </div>
</main>
