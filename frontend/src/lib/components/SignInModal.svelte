<script lang="ts">
  import { Checkbox } from '$components/dsfr'
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
  let closeButton: HTMLButtonElement

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
      closeButton.click()
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

<button id="fr-signin-trigger" class="hidden" data-fr-opened="false" aria-controls="fr-modal-signin">open</button>

<dialog aria-labelledby="fr-modal-title-signin" id="fr-modal-signin" class="fr-modal">
  <div class="fr-container fr-container--fluid fr-container-md">
    <div class="fr-grid-row fr-grid-row--center">
      <div class="fr-col-12 fr-col-md-10 fr-col-lg-9">
        <div class="fr-modal__body">
          <div class="fr-modal__content p-0!">
            <div class="md:grid grid-cols-2">

              <!-- Left column: form -->
              <div class="px-8 py-10">
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
                      class="fr-btn w-full! mt-6!"
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

                    <button type="submit" class="fr-btn w-full! mb-3!" disabled={loading}>
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

              <!-- Right column: close + info -->
              <div class="px-8 py-10">
                <div class="flex justify-end mb-6">
                  <button
                    bind:this={closeButton}
                    class="fr-btn fr-btn--tertiary-no-outline fr-btn--sm"
                    aria-controls="fr-modal-signin"
                    title={m['auth.modal.close']()}
                  >
                    {m['auth.modal.close']()}
                    <span aria-hidden="true" class="ml-1">×</span>
                  </button>
                </div>

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
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>
