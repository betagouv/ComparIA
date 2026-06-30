<script lang="ts">
  import { Checkbox, Modal } from '$components/dsfr'
  import { consumeAltchaToken } from '$lib/captcha.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { auth } from '$lib/auth.svelte'

  let step = $state<'email' | 'code'>('email')
  let email = $state('')
  let code = $state('')
  let consented = $state(false)
  let loading = $state(false)
  let error = $state<string | null>(null)

  function closeModal() {
    const el = document.getElementById('fr-modal-signin')
    if (el) {
      // @ts-expect-error - DSFR is globally available
      window.dsfr(el).modal.conceal()
    }
  }

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
      auth.user = { email: result.email }
      closeModal()
      useToast(m['auth.success'](), 4000)
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

<Modal id="fr-modal-signin" titleId="fr-modal-title-signin" sizeClass="fr-col-12 fr-col-md-10" contentClass="p-0!">
  <div class="md:grid grid-cols-2">

    <!-- Left column: form -->
    <div class="px-10 py-10">
      {#if step === 'email'}
        <h2 id="fr-modal-title-signin" class="text-primary! text-2xl! font-bold! mb-3!">
          {m['auth.modal.email.title']()}
        </h2>
        <p class="fr-text--sm mb-6! text-[--text-mention-grey]">
          {m['auth.modal.email.subtitle']()}
        </p>

        <form onsubmit={requestCode}>
          <div class="fr-input-group mb-5!">
            <label class="fr-label" for="auth-email">{m['auth.modal.email.emailLabel']()}</label>
            <input
              id="auth-email"
              class="fr-input"
              type="email"
              autocomplete="email"
              placeholder="john.doe@gmail.com"
              bind:value={email}
              required
              disabled={loading}
            />
          </div>

          <Checkbox
            id="auth-consent"
            bind:checked={consented}
            label={m['auth.modal.email.consent']()}
          />

          {#if error}
            <p class="fr-message fr-message--error mt-3!">{error}</p>
          {/if}

          <button
            type="submit"
            class="fr-btn w-full! mt-6! rounded-lg!"
            disabled={!consented || loading}
          >
            {loading ? m['auth.modal.email.submitting']() : m['auth.modal.email.submit']()}
          </button>
        </form>

      {:else}
        <h2 id="fr-modal-title-signin" class="text-primary! text-2xl! font-bold! mb-3!">
          {m['auth.modal.code.title']()}
        </h2>
        <p class="fr-text--sm mb-6! text-[--text-mention-grey]">
          {m['auth.modal.code.subtitle']({ email })}
        </p>

        <form onsubmit={verifyCode}>
          <div class="fr-input-group mb-5!">
            <label class="fr-label" for="auth-code">{m['auth.modal.code.label']()}</label>
            <input
              id="auth-code"
              class="fr-input"
              type="text"
              inputmode="numeric"
              maxlength={6}
              autocomplete="one-time-code"
              value={code}
              oninput={(e) => { code = e.currentTarget.value.replace(/\D/g, '').slice(0, 6) }}
              required
              disabled={loading}
            />
          </div>

          {#if error}
            <p class="fr-message fr-message--error mb-3!">{error}</p>
          {/if}

          <button type="submit" class="fr-btn w-full! mb-3! rounded-lg!" disabled={loading}>
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

    <!-- Right column: info -->
    <div class="bg-[--background-alt-grey] border-l border-[--border-default-grey] px-10 py-10">
      <h3 class="text-base! font-bold! mb-2!">{m['auth.modal.info.dataTitle']()}</h3>
      <p class="fr-text--sm mb-6!">{m['auth.modal.info.dataDesc']()}</p>

      <h3 class="text-base! font-bold! mb-2!">{m['auth.modal.info.datasetsTitle']()}</h3>
      <p class="fr-text--sm mb-2!">{@html m['auth.modal.info.datasetsDesc']()}</p>
      <ul class="fr-text--sm mb-4!">
        <li>{m['auth.modal.info.neverName']()}</li>
        <li>{m['auth.modal.info.neverAddress']()}</li>
        <li>{m['auth.modal.info.neverPhone']()}</li>
        <li>{m['auth.modal.info.neverPersonal']()}</li>
        <li>{m['auth.modal.info.neverOther']()}</li>
      </ul>
      <p class="fr-text--sm mb-0!">{m['auth.modal.info.emailPrivacy']()}</p>
    </div>

  </div>
</Modal>
