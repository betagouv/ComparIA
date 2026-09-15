<script lang="ts">
  import { replaceState } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Button, Checkbox, Input } from '$components/dsfr'
  import TotpCodeInput from '$components/TotpCodeInput.svelte'
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
  import { onMount, tick, untrack } from 'svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'
  import { SvelteURLSearchParams } from 'svelte/reactivity'
  import SurveyQuestionField, { type SurveyQuestion } from './SurveyQuestionField.svelte'

  let {
    onSuccess,
    onLegalNavigate,
    titleId,
    startAtTotp = false,
    hideHeader = false,
    ...props
  }: {
    onSuccess?: () => void
    onLegalNavigate?: (event: MouseEvent) => void
    /** Lets a wrapping modal point its aria-labelledby at this form's title. */
    titleId?: string
    /** The email code was already checked elsewhere: only the authenticator is left. */
    startAtTotp?: boolean
    /** Hides the internal title and subtitle when the host page already shows them. */
    hideHeader?: boolean
  } & SvelteHTMLElements['div'] = $props()

  const auth = getAuthContext()
  const platformName = getPlatformName()
  const locale = getLocale()
  let step = $state<'email' | 'code' | 'totp'>(untrack(() => (startAtTotp ? 'totp' : 'email')))
  let email = $state('')
  let code = $state('')
  let totpCode = $state('')
  let mergeComparisons = $state(false)
  let loading = $state(false)
  let error = $state<string>()

  let terms = $state<ConsentDocument>()
  let consentRequired = $state(false)
  let consented = $state(false)
  let consentLoading = $state(true)
  let consentError = $state<string>()
  let formContainer: HTMLDivElement

  // Blocking signup questions. A failed or empty fetch leaves this list
  // empty, which is deliberately indistinguishable from "no questions
  // configured": either way nothing here should stop sign-in.
  let surveyQuestions = $state<SurveyQuestion[]>([])
  let surveyLoading = $state(true)
  let surveyAnswers = $state<Record<string, string[]>>({})

  const consentLabel = $derived(terms ? consentCheckboxLabel(terms, true) : '')
  const canMergeComparisons = $derived(auth.config.access_policy === 'anonymous_first')
  // Opened straight at the authenticator step: there is no address to show
  // or change, the invite already checked it.
  const emailAlreadyChecked = $derived(startAtTotp && step === 'totp')
  // Optional questions are asked on this form and never hold it up, which is
  // the same rule the backend gate applies before it hands out a login code.
  const surveyAnswered = $derived(
    surveyQuestions
      .filter((question) => question.required)
      .every((question) => (surveyAnswers[question.id]?.length ?? 0) > 0)
  )

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

  async function loadSurveyQuestions(locale: string) {
    surveyLoading = true
    try {
      const data = await api.request<{ questions: SurveyQuestion[] }>('/survey/questions', {
        searchParams: { locale, trigger: 'signup' }
      })
      surveyQuestions = data.questions
    } catch {
      // A survey outage must never block sign-in: this degrades exactly like
      // no questions being configured at all.
      surveyQuestions = []
    } finally {
      surveyLoading = false
    }
  }

  onMount(() => {
    readConsent()
  })

  // Re-fetch the questions when the language changes while the form is open:
  // getLocale() is reactive, so tracking it here keeps the labels in step
  // with the rest of the page.
  $effect(() => {
    void loadSurveyQuestions(getLocale())
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
    if (!surveyAnswered) return
    loading = true
    error = undefined
    try {
      if (consentRequired) {
        await submitConsent(terms, false)
        consentRequired = false
      }
      if (surveyQuestions.length > 0) {
        // Submitted while still anonymous, alongside consent: the backend
        // attaches these to the anonymous session and carries them onto the
        // account once it exists.
        await api.request('/survey/answers', {
          method: 'POST',
          body: JSON.stringify({
            answers: surveyQuestions.map((question) => ({
              question_id: question.id,
              option_keys: surveyAnswers[question.id] ?? []
            }))
          })
        })
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

  async function signedIn() {
    const data = await api.request<{ user: AuthUser | null }>('/auth/me')
    auth.user = data.user
    if (mergeComparisons) {
      await api.request('/arena/comparison/merge', { method: 'POST' })
    }
    onSuccess?.()
    useToast(m['auth.success'](), 4000)
  }

  async function verifyCode() {
    loading = true
    error = undefined
    try {
      const { totp_required } = await api.request<{ email: string; totp_required: boolean }>(
        '/auth/email/verify',
        { method: 'POST', body: JSON.stringify({ email, code }) }
      )
      if (totp_required) {
        // Admins with an authenticator: no session yet, one more step.
        step = 'totp'
        loading = false
        await tick()
        formContainer.querySelector<HTMLInputElement>('#login-totp')?.focus()
        return
      }
      await signedIn()
    } catch {
      error = m['auth.modal.code.error']()
    } finally {
      loading = false
    }
  }

  async function verifyTotp() {
    loading = true
    error = undefined
    try {
      await api.request('/auth/totp/verify', {
        method: 'POST',
        body: JSON.stringify({ code: totpCode })
      })
      await signedIn()
    } catch (err) {
      const status = (err as ApiError).status
      if (status === 401 || status === 410) {
        // Too many wrong codes, the ten minutes ran out, or the challenge
        // cookie never reached us: start over.
        await restartAtEmail(m['auth.modal.totp.expired']())
      } else if (!status || status >= 500) {
        // Nothing reached the backend, or it could not answer: not a wrong code.
        error = m['errors.unknown']()
      } else {
        error = m['auth.modal.totp.error']()
      }
    } finally {
      loading = false
    }
  }

  async function restartAtEmail(message: string) {
    if (startAtTotp) {
      // The page was opened on the authenticator step; a reload must not
      // land there again now that the challenge behind it is gone.
      const params = new SvelteURLSearchParams(page.url.searchParams)
      params.delete('step')
      const qs = params.toString()
      replaceState(qs ? resolve(`${page.url.pathname}?${qs}`) : page.url.pathname, {})
    }
    step = 'email'
    code = ''
    totpCode = ''
    error = message
    // Enabled before the focus lands, or the field would still refuse it.
    loading = false
    await tick()
    formContainer.querySelector<HTMLInputElement>('#login-email')?.focus()
  }

  function onResend() {
    step = 'email'
    error = undefined
    code = ''
    totpCode = ''
    requestCode()
  }

  async function onChangeEmail() {
    step = 'email'
    error = undefined
    code = ''
    totpCode = ''
    await tick()
    formContainer.querySelector<HTMLInputElement>('#login-email')?.focus()
  }

  function onSubmit(e: SubmitEvent) {
    e.preventDefault()
    if (step === 'email') requestCode()
    else if (step === 'code') verifyCode()
    else verifyTotp()
  }
</script>

<div bind:this={formContainer} {...props} class={['py-10 px-8', props.class]}>
  {#if !hideHeader}
    <h2 id={titleId} class="fr-h4 text-primary! mb-4!">{m['auth.modal.email.title']()}</h2>
    <p class="text-xs! mb-6! text-grey">
      {m['auth.modal.email.subtitle']({ platformName })}
    </p>
  {/if}

  <form onsubmit={onSubmit}>
    {#if emailAlreadyChecked}
      <p class="text-sm! text-grey mb-4!">{m['auth.modal.totp.emailChecked']()}</p>
    {:else}
      <Input
        id="login-email"
        bind:value={email}
        type="email"
        label={m['auth.modal.email.emailLabel']()}
        error={step === 'email' ? error : undefined}
        disabled={loading || step !== 'email'}
        autocomplete="email"
        required
        class="mb-4!"
      />

      {#if step !== 'email'}
        <Button
          type="button"
          size="xs"
          variant="tertiary-no-outline"
          text={m['auth.modal.code.changeEmail']()}
          disabled={loading}
          onclick={onChangeEmail}
          class="-mt-2! mb-4! text-black! underline"
        />
      {/if}
    {/if}

    {#if surveyQuestions.length > 0}
      {#each surveyQuestions as question (question.id)}
        <SurveyQuestionField
          {question}
          optionalSuffix={m['survey.signup.optional']()}
          disabled={loading || step === 'code'}
          onchange={(option_keys) => (surveyAnswers[question.id] = option_keys)}
        />
      {/each}
    {/if}

    {#if canMergeComparisons}
      <Checkbox
        id="login-merge"
        class="text-xs! mt-1!"
        bind:checked={mergeComparisons}
        disabled={step !== 'email'}
        label={m['auth.modal.merge']()}
      />
    {/if}

    {#if terms}
      <Checkbox
        id="login-consent"
        class="text-xs! mt-1!"
        bind:checked={consented}
        disabled={loading || step !== 'email' || !consentRequired}
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

    {#if step === 'totp'}
      <TotpCodeInput
        id="login-totp"
        bind:value={totpCode}
        label={m['auth.modal.totp.label']()}
        help={m['auth.modal.totp.help']()}
        {error}
        disabled={loading}
        groupClass="mt-6!"
      />
      <Button
        type="submit"
        text={loading ? m['auth.modal.code.verifying']() : m['auth.modal.code.submit']()}
        disabled={loading || totpCode.length !== 6}
        class="mt-8 block! w-full!"
      />
    {:else if step === 'code'}
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
        disabled={loading ||
          consentLoading ||
          !terms ||
          (consentRequired && !consented) ||
          surveyLoading ||
          !surveyAnswered}
        class="mt-8 block! w-full!"
      />
    {/if}
  </form>
</div>
