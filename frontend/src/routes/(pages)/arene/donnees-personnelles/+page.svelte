<script lang="ts">
  import LegalDocument from '$components/LegalDocument.svelte'
  import PrivacyPolicyFallback from '$components/PrivacyPolicyFallback.svelte'
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'

  let { data } = $props()
</script>

<SeoHead title={m['seo.titles.donnees-personnelles']()} />

<main class="py-10 lg:py-15">
  <div class="fr-container">
    <h1 id="politique-de-confidentialite">{m['general.privacy.title']()}</h1>

    {#if data.privacyPolicy}
      <LegalDocument
        version={data.privacyPolicy.version}
        effectiveAt={data.privacyPolicy.effective_at}
        content={data.privacyPolicy.content}
      />
    {:else}
      <PrivacyPolicyFallback />
    {/if}
  </div>
</main>
