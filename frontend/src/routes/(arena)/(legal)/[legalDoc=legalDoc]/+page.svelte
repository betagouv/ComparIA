<script lang="ts">
  import LegalDocument from '$components/LegalDocument.svelte'
  import MatomoOptOut from '$components/MatomoOptOut.svelte'
  import { SeoHead } from '$components/layout'
  import type { LegalDocumentKeys } from '$lib/generated/constants'
  import { m } from '$lib/i18n/messages'
  import type { PageProps } from './$types'

  const { data, params }: PageProps = $props()
  const legalDocKey = $derived(params.legalDoc as LegalDocumentKeys)
</script>

<SeoHead title={m[`seo.titles.${legalDocKey}`]()} />

<div class="py-10 lg:py-15">
  <div class="fr-container">
    <h1>{m[`general.${legalDocKey}.title`]()}</h1>

    {#if data.doc}
      <LegalDocument
        version={data.doc.version}
        effectiveAt={data.doc.effective_at}
        content={data.doc.content}
        locale={data.doc.locale}
      />
    {:else}
      <p class="fr-alert fr-alert--error" role="alert">{m['general.document.unavailable']()}</p>
    {/if}

    <!-- The published policy is sanitized Markdown and cannot carry the script. -->
    {#if legalDocKey === 'privacy_policy' && data.matomoUrl}
      <h2 id="matomo-opt-out-title">{m['general.privacy_policy.optOutTitle']()}</h2>
      <MatomoOptOut url={data.matomoUrl} />
    {/if}
  </div>
</div>
