<script lang="ts">
  import LegalDocument from '$components/LegalDocument.svelte'
  import MatomoOptOut from '$components/MatomoOptOut.svelte'
  import { Button } from '$components/dsfr'
  import { SeoHead } from '$components/layout'
  import type { LegalDocumentKeys } from '$lib/generated/constants'
  import { m } from '$lib/i18n/messages'
  import { getCookieConsentContext } from '$lib/stores/cookieConsent.svelte'
  import type { PageProps } from './$types'

  const { data, params }: PageProps = $props()
  const legalDocKey = $derived(params.legalDoc as LegalDocumentKeys)
  const cookieConsent = getCookieConsentContext()
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

    {#if legalDocKey === 'privacy_policy' && cookieConsent.asking}
      <!-- The opt-out iframe would load Matomo before the visitor says yes. -->
      <h2 id="cookie-choice-title">{m['general.privacy_policy.cookiesTitle']()}</h2>
      <Button
        variant="secondary"
        text={m['cookieBanner.manage']()}
        onclick={() => cookieConsent.reopen()}
      />
    {:else if legalDocKey === 'privacy_policy' && data.measurement && cookieConsent.decision.loadMeasurement}
      <!-- The published policy is sanitized Markdown and cannot carry the script.
           The Matomo in use comes from the root layout. While the tracker is
           held back, so is the opt-out, which loads from the same server. -->
      <h2 id="matomo-opt-out-title">{m['general.privacy_policy.optOutTitle']()}</h2>
      <MatomoOptOut url={data.measurement.url} />
    {/if}
  </div>
</div>
