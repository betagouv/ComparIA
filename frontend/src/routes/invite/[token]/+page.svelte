<script lang="ts">
  import { goto } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Button, Checkbox, Link } from '$components/dsfr'
  import { getAuthContext, type AuthUser } from '$lib/auth.svelte'
  import {
    consentCheckboxLabel,
    legalLinks,
    loadConsent,
    reloadConsent,
    submitConsent,
    type ConsentDocument
  } from '$lib/consent'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { onMount } from 'svelte'

  const auth = getAuthContext()
  const locale = getLocale()
  const token = $derived(page.params.token)

  let checkStatus = $state<'loading' | 'valid' | 'invalid'>('loading')
  let consented = $state(false)
  let submitting = $state(false)
  let error = $state<string>()

  let terms = $state<ConsentDocument>()
  let consentRequired = $state(false)
  let consentLoading = $state(true)
  let consentError = $state<string>()

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

  onMount(async () => {
    readConsent()
    try {
      const result = await api.request<{ valid: boolean }>(`/auth/invite/${token}`)
      checkStatus = result.valid ? 'valid' : 'invalid'
    } catch {
      checkStatus = 'invalid'
    }
  })

  $effect(() => {
    if (consented && terms) consentError = undefined
  })

  async function accept() {
    if (!terms) {
      consentError = m['consent.loadFailed']()
      return
    }
    if (consentRequired && !consented) {
      consentError = m['consent.required']()
      return
    }
    submitting = true
    error = undefined
    try {
      // Recorded while still anonymous, so accept_invite carries it onto the
      // new account with the time it was given.
      if (consentRequired) {
        await submitConsent(terms, false)
        consentRequired = false
      }
      await api.request('/auth/invite/accept', {
        method: 'POST',
        body: JSON.stringify({ token })
      })
      const data = await api.request<{ user: AuthUser | null }>('/auth/me')
      auth.user = data.user
      useToast(m['auth.success'](), 4000)
      goto(resolve('/'))
    } catch (err) {
      error = (err as Error).message
      checkStatus = 'invalid'
    } finally {
      submitting = false
    }
  }
</script>

<svelte:head>
  <title>Invitation — compar:IA</title>
</svelte:head>

<div class="md:flex-row flex min-h-screen flex-col">
  <header class="px-8 py-10 gap-20 md:justify-center flex basis-1/2 flex-col">
    <div class="gap-2 flex items-center">
      <img
        src={auth.config?.has_custom_logo ? api.getUrl('/auth/config/logo') : '/orgs/comparia.png'}
        aria-hidden="true"
        alt=""
        class="h-[35px]"
      />
      <h1 class="font-bold text-base! mb-0!">
        {auth.config?.platform_name || m['header.title']()}
      </h1>
    </div>

    <div>
      <h2 class="fr-h5 mb-4!">{m['invite.title']()}</h2>
    </div>
  </header>

  <main class="bg-light-grey md:flex md:items-center flex-auto basis-1/2">
    <div class="my-10 mx-8 md:max-w-[350px]">
      {#if checkStatus === 'invalid'}
        <p class="text-sm! mb-6!">{m['invite.invalid']()}</p>
        <Link button href="/login" text={m['invite.backToLogin']()} />
      {:else if checkStatus === 'valid'}
        {#if terms}
          <Checkbox
            id="invite-consent"
            class="text-xs!"
            bind:checked={consented}
            disabled={submitting || !consentRequired}
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
        <Button
          text={submitting ? m['invite.accepting']() : m['invite.accept']()}
          disabled={submitting || consentLoading || !terms || (consentRequired && !consented)}
          onclick={accept}
          class="mt-4 block! w-full!"
        />
        {#if error}
          <p class="fr-error-text fr-text--sm mt-2!">{error}</p>
        {/if}
      {/if}
    </div>
  </main>
</div>
