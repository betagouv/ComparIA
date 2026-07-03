<script lang="ts">
  import { goto } from '$app/navigation'
  import { page } from '$app/state'
  import { Checkbox } from '$components/dsfr'
  import { env } from '$env/dynamic/public'
  import { auth } from '$lib/auth.svelte'
  import { consumeAltchaToken } from '$lib/captcha.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  let step = $state<'email' | 'code'>('email')
  let email = $state('')
  let code = $state('')
  let consented = $state(false)
  let loading = $state(false)
  let error = $state<string | null>(null)

  const redirectTo = $derived(page.url.searchParams.get('redirect') || '/arene')

  const loginTitle = env.PUBLIC_AUTH_LOGIN_TITLE || 'Bienvenue sur compar:IA'
  const loginDescription =
    env.PUBLIC_AUTH_LOGIN_DESCRIPTION ||
    "Comparez les modèles d'IA conversationnelle en aveugle et contribuez à l'évaluation de l'IA en Europe."

  onMount(() => {
    if (auth.user) goto(redirectTo)
  })

  async function requestCode(e: SubmitEvent) {
    e.preventDefault()
    loading = true
    error = null
    try {
      const altcha_payload = await consumeAltchaToken()
      await api.request('/auth/email/request', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, altcha_payload })
      })
      step = 'code'
    } catch (err) {
      error = (err as Error).message
    } finally {
      loading = false
    }
  }

  async function verifyCode(e: SubmitEvent) {
    e.preventDefault()
    loading = true
    error = null
    try {
      const result = await api.request<{ email: string }>('/auth/email/verify', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code })
      })
      auth.user = { email: result.email, role: 'user' }
      useToast(m['auth.success'](), 4000)
      goto(redirectTo)
    } catch {
      error = m['auth.modal.code.error']()
    } finally {
      loading = false
    }
  }

  function backToEmail() {
    step = 'email'
    error = null
    code = ''
  }
</script>

<svelte:head>
  <title>Connexion — compar:IA</title>
</svelte:head>

<div class="flex min-h-screen flex-col bg-[--background-alt-grey]">
  <header class="px-8 py-5 bg-white border-b border-[--border-default-grey]">
    <span class="fr-text--sm font-medium">compar:IA</span>
  </header>

  <main class="px-4 py-16 flex flex-1 items-center justify-center">
    <div class="max-w-3xl bg-white shadow-sm fr-grid-row w-full overflow-hidden">
      <div
        class="fr-col-12 fr-col-md-5 px-10 py-12 flex flex-col justify-center bg-[--background-alt-grey]"
      >
        <h1 class="fr-h5 mb-4!">{loginTitle}</h1>
        <p class="fr-text--sm mb-0! text-[--text-mention-grey]">{loginDescription}</p>
      </div>

      <div class="fr-col-12 fr-col-md-7 px-10 py-12">
        {#if step === 'email'}
          <h2 class="fr-h6 text-primary! mb-3!">{m['auth.modal.email.title']()}</h2>
          <p class="fr-text--sm mb-6! text-[--text-mention-grey]">
            {m['auth.modal.email.subtitle']()}
          </p>

          <form onsubmit={requestCode}>
            <div class="fr-input-group mb-5!">
              <label class="fr-label" for="login-email">{m['auth.modal.email.emailLabel']()}</label>
              <input
                id="login-email"
                class="fr-input"
                type="email"
                autocomplete="email"
                placeholder="prenom.nom@organisation.fr"
                bind:value={email}
                required
                disabled={loading}
              />
            </div>

            <Checkbox
              id="login-consent"
              bind:checked={consented}
              label={m['auth.modal.email.consent']()}
            />

            {#if error}
              <p class="fr-message fr-message--error mt-3!">{error}</p>
            {/if}

            <button type="submit" class="fr-btn mt-6! w-full!" disabled={!consented || loading}>
              {loading ? m['auth.modal.email.submitting']() : m['auth.modal.email.submit']()}
            </button>
          </form>
        {:else}
          <h2 class="fr-h6 text-primary! mb-3!">{m['auth.modal.code.title']()}</h2>
          <p class="fr-text--sm mb-6! text-[--text-mention-grey]">
            {m['auth.modal.code.subtitle']({ email })}
          </p>

          <form onsubmit={verifyCode}>
            <div class="fr-input-group mb-5!">
              <label class="fr-label" for="login-code">{m['auth.modal.code.label']()}</label>
              <input
                id="login-code"
                class="fr-input"
                type="text"
                inputmode="numeric"
                maxlength={6}
                autocomplete="one-time-code"
                value={code}
                oninput={(e) => {
                  code = e.currentTarget.value.replace(/\D/g, '').slice(0, 6)
                }}
                required
                disabled={loading}
              />
            </div>

            {#if error}
              <p class="fr-message fr-message--error mb-3!">{error}</p>
            {/if}

            <button type="submit" class="fr-btn mb-3! w-full!" disabled={loading}>
              {loading ? m['auth.modal.code.verifying']() : m['auth.modal.code.submit']()}
            </button>

            <button
              type="button"
              class="fr-btn fr-btn--tertiary-no-outline w-full!"
              onclick={backToEmail}
            >
              {m['auth.modal.code.resend']()}
            </button>
          </form>
        {/if}
      </div>
    </div>
  </main>
</div>
