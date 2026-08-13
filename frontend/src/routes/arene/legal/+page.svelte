<script lang="ts">
  import InformationalPageContent from '$components/InformationalPageContent.svelte'
  import LegalNoticeFallback from '$components/LegalNoticeFallback.svelte'
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'

  let { data } = $props()
</script>

{#if data.content}
  <SeoHead title={m['seo.titles.mentions-legales']()} />
  <div class="py-10 lg:py-15">
    <div class="fr-container">
      <h1 id="mentions-legales" class="fr-h2">{m['general.legal.title']()}</h1>
      <InformationalPageContent content={data.content} />
    </div>
  </div>
{:else}
  <LegalNoticeFallback />
{/if}
