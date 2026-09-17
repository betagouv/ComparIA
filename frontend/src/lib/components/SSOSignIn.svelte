<script lang="ts">
  import { Button, Checkbox } from '$components/dsfr'
  import { getAuthContext } from '$lib/auth.svelte'
  import {
    consentCheckboxLabel,
    legalLinks,
    loadConsent,
    reloadConsent,
    submitConsent,
    type ConsentDocument
  } from '$lib/consent'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import type { ExternalHref } from '$lib/routing'
  import { onMount } from 'svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    oidcLabel,
    oidcLogoUrl,
    onLegalNavigate,
    ...props
  }: {
    oidcLabel: string
    oidcLogoUrl: string | null
    onLegalNavigate?: (event: MouseEvent) => void
  } & SvelteHTMLElements['div'] = $props()

  const auth = getAuthContext()
  const locale = getLocale()
  const loginUrl = api.getUrl('/auth/oidc/login') as ExternalHref

  let terms = $state<ConsentDocument>()
  let consentRequired = $state(false)
  let consented = $state(false)
  let consentLoading = $state(true)
  let consentError = $state<string>()
  let loading = $state(false)

  const consentLabel = $derived(terms ? consentCheckboxLabel(terms, true) : '')

  async function readConsent(again = false) {
    consentLoading = true
    consentError = undefined
    try {
      const snapshot = await (again ? reloadConsent : loadConsent)(locale, false)
      terms = snapshot.document
      consentRequired = !snapshot.accepted
      consented = snapshot.accepted
    } catch {
      terms = undefined
      consentError = m['consent.loadFailed']()
    } finally {
      consentLoading = false
    }
  }

  onMount(() => {
    readConsent()
  })

  async function onSignIn() {
    if (!terms) {
      consentError = m['consent.loadFailed']()
      return
    }
    if (consentRequired && !consented) {
      consentError = m['consent.required']()
      return
    }
    loading = true
    try {
      // The backend gate on /auth/oidc/login requires a recorded acceptance
      // before it redirects to the provider, so record it first — the email
      // form does the same just before requesting its code.
      if (consentRequired) {
        await submitConsent(terms, false)
      }
      window.location.href = loginUrl
    } catch {
      consentError = m['consent.loadFailed']()
      loading = false
    }
  }
</script>

<div {...props} class={['my-10 mx-8', props.class]}>
  <p class="text-xs! mb-6! text-grey">{m['auth.oidc.panelSubtitle']()}</p>

  <Button
    variant="secondary"
    onclick={onSignIn}
    disabled={loading || consentLoading || !terms || (consentRequired && !consented)}
    class="block w-full! justify-center"
  >
    <span class="gap-2 inline-flex items-center justify-center">
      {#if oidcLogoUrl}
        <img src={oidcLogoUrl} alt="" class="h-8" />
      {/if}
      {oidcLabel}
    </span>
  </Button>

  {#if terms}
    <Checkbox
      id="sso-consent"
      class="text-xs! mt-4!"
      bind:checked={consented}
      disabled={loading || consentLoading || !consentRequired}
      label={consentLabel}
      links={legalLinks()}
      linksClass="text-xs! leading-5!"
      onLinkClick={onLegalNavigate}
      error={consentError}
    />
  {:else if consentError}
    <p class="fr-error-text fr-text--sm mt-2!" role="alert">{consentError}</p>
    <Button
      size="sm"
      variant="secondary"
      text={m['consent.retry']()}
      disabled={consentLoading}
      onclick={() => readConsent(true)}
    />
  {/if}
</div>
