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
    redirect = null,
    onLegalNavigate,
    ...props
  }: {
    oidcLabel: string
    oidcLogoUrl: string | null
    /** App-relative path the callback sends the user back to after sign-in. */
    redirect?: string | null
    onLegalNavigate?: (event: MouseEvent) => void
  } & SvelteHTMLElements['div'] = $props()

  const auth = getAuthContext()
  const locale = getLocale()

  let terms = $state<ConsentDocument>()
  let consentRequired = $state(false)
  let consented = $state(false)
  let consentLoading = $state(true)
  let consentError = $state<string>()
  let mergeComparisons = $state(false)
  let loading = $state(false)

  const consentLabel = $derived(terms ? consentCheckboxLabel(terms, true) : '')
  const canMergeComparisons = $derived(auth.config.access_policy === 'anonymous_first')

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
      const searchParams: Record<string, string> = {}
      if (redirect) searchParams.redirect = redirect
      if (canMergeComparisons && mergeComparisons) searchParams.merge = '1'
      window.location.href = api.getUrl('/auth/oidc/login', searchParams) as ExternalHref
    } catch {
      consentError = m['consent.loadFailed']()
      loading = false
    }
  }
</script>

<div {...props} class={['my-10 mx-8', props.class]}>
  <p class="text-xs! mb-6! text-grey">{m['auth.oidc.panelSubtitle']()}</p>

  <!-- Same order as the email form: the boxes the button depends on come
       first, so a disabled button never waits on something below it. -->
  {#if canMergeComparisons}
    <Checkbox
      id="sso-merge"
      class="text-xs! mt-1!"
      bind:checked={mergeComparisons}
      disabled={loading}
      label={m['auth.modal.merge']()}
    />
  {/if}

  {#if terms}
    <Checkbox
      id="sso-consent"
      class="text-xs! mt-1!"
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

  <Button
    variant="secondary"
    onclick={onSignIn}
    disabled={loading || consentLoading || !terms || (consentRequired && !consented)}
    class="mt-8 block w-full! justify-center"
  >
    <!-- A long label wraps beside its logo rather than centring under it. -->
    <span class="gap-3 inline-flex items-center text-left">
      {#if oidcLogoUrl}
        <img src={oidcLogoUrl} alt="" class="h-8 shrink-0" />
      {/if}
      <span>{oidcLabel}</span>
    </span>
  </Button>
</div>
