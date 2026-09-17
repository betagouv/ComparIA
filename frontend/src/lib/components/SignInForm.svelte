<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Button, Checkbox, Input } from '$components/dsfr'
  import SurveyFormSignup from '$components/SurveyFormSignup.svelte'
  import { getAuthContext, type AuthUser } from '$lib/auth.svelte'
  import { getPlatformName } from '$lib/authContext.svelte'
  import { consumeAltchaToken } from '$lib/captcha.svelte'
  import {
    consentCheckboxLabel,
    legalLinks,
    loadConsent,
    reloadConsent,
    submitConsent,
    type ConsentDocument
  } from '$lib/consent'
  import { api, type ApiError } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { getSurveyContext } from '$lib/survey'
  import { onMount, tick } from 'svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    step = $bindable('email'),
    onSuccess,
    onLegalNavigate,
    titleId,
    ...props
  }: {
    step?: 'email' | 'code' | 'questions'
    onSuccess?: () => void
    onLegalNavigate?: (event: MouseEvent) => void
    /** Lets a wrapping modal point its aria-labelledby at this form's title. */
    titleId?: string
  } & SvelteHTMLElements['div'] = $props()

  const auth = getAuthContext()
  const platformName = getPlatformName()
  const survey = getSurveyContext()
  const locale = getLocale()
  let email = $state('')
  let code = $state('')
  let mergeComparisons = $state(false)
  let loading = $state(false)
  let error = $state<string>()

  let terms = $state<ConsentDocument>()
  let consentRequired = $state(false)
  let consented = $state(false)
  let consentLoading = $state(true)
  let consentError = $state<string>()
  let formContainer: HTMLDivElement

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

  $effect(() => {
    if (consented && terms) consentError = undefined
  })

  async function requestCode() {
    if (!terms) {
      consentError = m['consent.loadFailed']()
      return
    }
    if (consentRequired && !consented) {
      consentError = m['consent.required']()
      return
    }
    loading = true
    error = undefined
    try {
      if (consentRequired) {
        await submitConsent(terms, false)
        consentRequired = false
      }
      const altcha_payload = await consumeAltchaToken()
      await api.request('/auth/email/request', {
        method: 'POST',
        body: JSON.stringify({ email, altcha_payload, locale })
      })
      step = 'code'
    } catch (err) {
      // A 428 here means the backend has required signup questions this form
      // does not show: the fetch failed, or an admin added one while the page
      // sat open. Either way the two sides contradict each other, reloading
      // fixes both, and the raw refusal is untranslated.
      error =
        (err as ApiError).status === 428
          ? m['survey.signup.reloadNeeded']()
          : (err as Error).message
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
      if (mergeComparisons) {
        await api.request('/arena/comparison/merge', { method: 'POST' })
      }
      const data = await api.request<{ user: AuthUser | null }>('/auth/me')
      auth.user = data.user
      await invalidate('survey:signup')
      const newUser = Date.now() - new Date(auth.user!.created_at).getTime() < 60 * 60 * 1000
      // Ask questions if any and user didn't yet answered it
      if (survey.signupQuestions.length && (!auth.user!.questionsAnswered || newUser)) {
        step = 'questions'
      } else {
        onLoginCompleted()
      }
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

  async function onChangeEmail() {
    step = 'email'
    error = undefined
    code = ''
    await tick()
    formContainer.querySelector<HTMLInputElement>('#login-email')?.focus()
  }

  function onSubmit(e: SubmitEvent) {
    e.preventDefault()
    if (step === 'email') requestCode()
    else verifyCode()
  }

  function onLoginCompleted() {
    onSuccess?.()
    useToast(m['auth.success'](), 4000)
    step = 'email'
  }
</script>

<div bind:this={formContainer} {...props} class={['my-10 mx-8', props.class]}>
  {#if step !== 'questions'}
    <h2 id={titleId} class="fr-h4 text-primary! mb-4!">{m['auth.modal.email.title']()}</h2>
    <p class="text-xs! mb-6! text-grey">
      {m['auth.modal.email.subtitle']({ platformName })}
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

      {#if step === 'code'}
        <Button
          type="button"
          size="xs"
          variant="tertiary-no-outline"
          text={m['auth.modal.code.changeEmail']()}
          disabled={loading}
          onclick={onChangeEmail}
          class="-mt-2! mb-4! text-black! underline"
        />

        {#if canMergeComparisons}
          <Checkbox
            id="login-merge"
            class="text-xs! mt-1!"
            bind:checked={mergeComparisons}
            disabled={step === 'code'}
            label={m['auth.modal.merge']()}
          />
        {/if}
      {/if}

      {#if terms}
        <Checkbox
          id="login-consent"
          class="text-xs! mt-1!"
          bind:checked={consented}
          disabled={loading || step === 'code' || !consentRequired}
          label={consentLabel}
          links={legalLinks()}
          linksClass="text-xs! leading-5!"
          onLinkClick={onLegalNavigate}
          error={consentError}
        />
      {:else if consentError}
        <p class="fr-error-text fr-text--sm" role="alert">{consentError}</p>
        <Button
          size="sm"
          variant="secondary"
          text={m['consent.retry']()}
          disabled={consentLoading}
          onclick={() => readConsent(true)}
        />
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
          disabled={loading || consentLoading || !terms || (consentRequired && !consented)}
          class="mt-8 block! w-full!"
        />
      {/if}
    </form>
  {:else}
    <SurveyFormSignup
      id="signin-survey"
      title={m['survey.afterVote.title']()}
      questions={survey.signupQuestions}
      answers={survey.signupAnswers}
      onSuccess={onLoginCompleted}
    />
  {/if}
</div>
