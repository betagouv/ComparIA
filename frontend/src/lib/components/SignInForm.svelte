<script lang="ts">
  import { Button, Checkbox, Input } from '$components/dsfr'
  import { getAuthContext, type AuthUser } from '$lib/auth.svelte'
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
  import { onMount } from 'svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'
  import SurveyQuestionField, { type SurveyQuestion } from './SurveyQuestionField.svelte'

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
  let consented = $state(false)
  let consentLoading = $state(true)
  let consentError = $state<string>()

  // Blocking signup questions. A failed or empty fetch leaves this list
  // empty, which is deliberately indistinguishable from "no questions
  // configured": either way nothing here should stop sign-in.
  let surveyQuestions = $state<SurveyQuestion[]>([])
  let surveyLoading = $state(true)
  let surveyAnswers = $state<Record<string, string[]>>({})

  const consentLabel = $derived(terms ? consentCheckboxLabel(terms, true) : '')
  const canMergeComparisons = $derived(auth.config.access_policy === 'anonymous_first')
  const surveyAnswered = $derived(
    surveyQuestions.every((question) => (surveyAnswers[question.id]?.length ?? 0) > 0)
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

  async function loadSurveyQuestions() {
    surveyLoading = true
    try {
      const data = await api.request<{ questions: SurveyQuestion[] }>(
        `/survey/questions?trigger=signup&locale=${encodeURIComponent(locale)}`
      )
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
    loadSurveyQuestions()
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
        body: JSON.stringify({ email, altcha_payload })
      })
      step = 'code'
    } catch (err) {
      // A 428 here means the backend has signup questions this form does not
      // show, which is what a failed question fetch leaves behind. Without
      // this the two sides contradict each other: no questions on screen, and
      // a refusal that asks for answers to them.
      error =
        (err as ApiError).status === 428 && surveyQuestions.length === 0
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

    {#if surveyQuestions.length > 0}
      <p class="text-xs! mt-4! mb-2! text-grey">
        {m['survey.signup.intro']()}
      </p>
      {#each surveyQuestions as question (question.id)}
        <SurveyQuestionField
          {question}
          disabled={loading || step === 'code'}
          onchange={(option_keys) => (surveyAnswers[question.id] = option_keys)}
        />
      {/each}
    {/if}

    {#if canMergeComparisons}
      <Checkbox
        id="login-merge"
        class="text-xs!"
        bind:checked={mergeComparisons}
        disabled={step === 'code'}
        label={m['auth.modal.merge']()}
      />
    {/if}

    {#if terms}
      <Checkbox
        id="login-consent"
        class="text-xs!"
        bind:checked={consented}
        disabled={loading || step === 'code' || !consentRequired}
        label={consentLabel}
        links={legalLinks()}
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
