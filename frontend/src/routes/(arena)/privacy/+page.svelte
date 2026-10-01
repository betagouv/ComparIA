<script lang="ts">
  import LegalDocument from '$components/LegalDocument.svelte'
  import MatomoOptOut from '$components/MatomoOptOut.svelte'
  import PrivacyPolicyFallback from '$components/PrivacyPolicyFallback.svelte'
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import type { PageProps } from './$types'

  const { data }: PageProps = $props()
</script>

<SeoHead title={m['seo.titles.donnees-personnelles']()} />

<div class="py-10 lg:py-15">
  <div class="fr-container">
    <h1 id="politique-de-confidentialite">{m['general.privacy.title']()}</h1>

    {#if data.privacyPolicy}
      <LegalDocument
        version={data.privacyPolicy.version}
        effectiveAt={data.privacyPolicy.effective_at}
        content={data.privacyPolicy.content}
        locale={data.privacyPolicy.locale}
      />
      <!-- The published policy is sanitized Markdown and cannot carry the script. -->
      {#if data.matomoUrl}
        <h2 id="matomo-opt-out-title">{m['general.privacy.optOutTitle']()}</h2>
        <MatomoOptOut url={data.matomoUrl} />
      {/if}
    {:else}
      <PrivacyPolicyFallback matomoUrl={data.matomoUrl} />
    {/if}
  </div>
</div>
