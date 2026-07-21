<script lang="ts">
  import { Button, Checkbox, Input } from '$components/dsfr'
  import { getAuthContext, type AuthUser } from '$lib/auth.svelte'
  import { consumeAltchaToken } from '$lib/captcha.svelte'
  import {
    buildConsentCheckboxLabel,
    buildConsentEvidence,
    getActiveTerms,
    getConsentStatus,
    serverHasCurrentAcceptance,
    storeConsent,
    CANONICAL_LEGAL_LINKS,
    type ConsentDocument
  } from '$lib/consent'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { onMount } from 'svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    onSuccess,
    ...props
  }: {
    onSuccess?: () => void
  } & SvelteHTMLElements['div'] = $props()

  const auth = getAuthContext()
  const locale = getLocale()
  let step = $state<'email' | 'code'>('email')
  let email = $state('')
  let code = $state('')
  let mergeComparisons = $state(false)
  let loading = $state(false)
  let error = $state<string>()
  let terms = $state<ConsentDocument>()
  let consentRequired = $state(false)
  let consentChecked = $state(false)
  let consentLoading = $state(true)
  let consentError = $state<string>()
  const consentLabel = $derived(terms ? buildConsentCheckboxLabel(terms, true) : '')
  const showConsent = $derived(consentRequired || consentChecked)

  onMount(async () => {
    try {
      const activeTerms = await getActiveTerms(locale)
      const status = await getConsentStatus(false)
      terms = activeTerms
      consentRequired = !serverHasCurrentAcceptance(activeTerms, status)
    } catch {
      consentError =
        'Les conditions de participation ne peuvent pas être chargées. Réessayez avant de demander un code.'
    } finally {
      consentLoading = false
    }
  })

  $effect(() => {
    if (consentChecked && terms) consentError = undefined
  })

  async function requestCode() {
    if (consentLoading || !terms) {
      consentError ??=
        'Les conditions de participation doivent être chargées avant de demander un code.'
      return
    }
    if (consentRequired && (!consentChecked || !terms)) {
      consentError = 'Vous devez accepter les conditions de participation avant de continuer.'
      return
    }
    loading = true
    error = undefined
    try {
      if (consentRequired && terms) {
        const consent = buildConsentEvidence(terms)
        await api.request('/auth/consent/anonymous', {
          method: 'POST',
          body: JSON.stringify({ consent })
        })
        storeConsent(consent)
        consentRequired = false
      }
      const altcha_payload = await consumeAltchaToken()
      await api.request('/auth/email/request', {
        method: 'POST',
        body: JSON.stringify({ email, altcha_payload })
      })
      step = 'code'
    } catch (err) {
      error = (err as Error).message
    } finally {
      loading = false
    }
  }

  async function verifyCode() {
    loading = true
    error = undefined
    try {
      await api.request<{ email: string }>('/auth/email/verify', {
        method: 'POST',
        body: JSON.stringify({ email, code })
      })
      const data = await api.request<{ user: AuthUser | null }>('/auth/me')
      auth.user = data.user
      if (mergeComparisons) {
        await api.request('/arena/comparison/merge', { method: 'POST' })
      }
      onSuccess?.()
      useToast(m['auth.success'](), 4000)
    } catch {
      error = m['auth.modal.code.error']()
    } finally {
      loading = false
    }
  }

  function onResend() {
    step = 'email'
    error = undefined
    code = ''
    requestCode()
  }

  function onSubmit(e: SubmitEvent) {
    e.preventDefault()
    if (step === 'email') requestCode()
    else verifyCode()
  }
</script>

<div {...props} class={['my-10 mx-8', props.class]}>
  <h2 class="fr-h4 text-primary! mb-4!">{m['auth.modal.email.title']()}</h2>
  <p class="text-xs! mb-6! text-grey">
    {m['auth.modal.email.subtitle']()}
  </p>

  <form onsubmit={onSubmit}>
    <Input
      id="login-email"
      bind:value={email}
      type="email"
      label={m['auth.modal.email.emailLabel']()}
      error={step === 'email' ? error : undefined}
      disabled={loading || step === 'code'}
      autocomplete="email"
      required
      class="mb-4!"
    />

    {#if auth.config.access_policy === 'anonymous_first'}
      <Checkbox
        id="login-merge"
        class="text-xs!"
        bind:checked={mergeComparisons}
        disabled={step === 'code'}
        label={m['auth.modal.merge']()}
      />
    {/if}

    {#if showConsent}
      <Checkbox
        id="login-consent"
        class="text-xs!"
        bind:checked={consentChecked}
        disabled={loading || step === 'code' || !consentRequired}
        label={consentLabel}
        links={CANONICAL_LEGAL_LINKS}
        error={consentError}
      />
    {:else if consentError}
      <p class="fr-error-text fr-text--sm" role="alert">{consentError}</p>
    {/if}

    {#if step === 'code'}
      <Input
        id="login-code"
        bind:value={code}
        type="text"
        label={m['auth.modal.code.label']()}
        {error}
        disabled={loading}
        inputmode="numeric"
        maxlength={6}
        autocomplete="one-time-code"
        oninput={(e) => {
          code = e.currentTarget.value.replace(/\D/g, '').slice(0, 6)
        }}
        required
        groupClass="mt-6!"
      />
      <Button
        type="submit"
        text={loading ? m['auth.modal.code.verifying']() : m['auth.modal.code.submit']()}
        disabled={loading}
        class="mt-8 block! w-full!"
      />

      <div class="mt-3 flex items-center justify-between">
        <p class="text-sm! text-grey mb-0!">
          {m['auth.modal.code.notReceived']()}
        </p>
        <Button
          size="xs"
          variant="tertiary-no-outline"
          text={m['auth.modal.code.resend']()}
          disabled={loading}
          onclick={() => onResend()}
          class="text-black! underline"
        />
      </div>
    {:else}
      <Button
        type="submit"
        text={loading ? m['auth.modal.email.submitting']() : m['auth.modal.email.submit']()}
        disabled={loading || consentLoading || !terms}
        class="mt-8 block! w-full!"
      />
    {/if}
  </form>
</div>
