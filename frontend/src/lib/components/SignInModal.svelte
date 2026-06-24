<script lang="ts">
  import { Checkbox } from '$components/dsfr'
  import { consumeAltchaToken } from '$lib/captcha.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
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
      useToast('Vous etes connecte !', 4000)
    } catch {
      error = 'Code invalide ou expire.'
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
                    Se connecter ou s'inscrire
                  </h2>
                  <p class="fr-text--sm mb-6! text-[--text-mention-grey]">
                    Accelez a votre historique de discussion et a un quota plus eleve d'utilisation
                    de modeles en etant connecte. La creation de compte reste facultative sur
                    compar:IA
                  </p>

                  <form onsubmit={requestCode}>
                    <div class="fr-input-group mb-5!">
                      <label class="fr-label" for="auth-email">Email</label>
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
                      label="J'ai pris connaissance de l'utilisation de mes donnees et j'accepte les <a href='/modalites' target='_blank'>conditions generales d'utilisation</a>"
                    />

                    {#if error}
                      <p class="fr-message fr-message--error mt-3!">{error}</p>
                    {/if}

                    <button
                      type="submit"
                      class="fr-btn w-full! mt-6!"
                      disabled={!consented || loading}
                    >
                      {loading ? 'Envoi en cours...' : 'Recevoir le code de connexion'}
                    </button>
                  </form>

                {:else}
                  <h2 id="fr-modal-title-signin" class="text-primary! text-2xl! font-bold! mb-3!">
                    Entrez votre code
                  </h2>
                  <p class="fr-text--sm mb-6! text-[--text-mention-grey]">
                    Un code a 6 chiffres a été envoyé a <strong>{email}</strong>.
                  </p>

                  <form onsubmit={verifyCode}>
                    <div class="fr-input-group mb-5!">
                      <label class="fr-label" for="auth-code">Code a 6 chiffres</label>
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
                      {loading ? 'Verification...' : 'Valider'}
                    </button>

                    <button
                      type="button"
                      class="fr-btn fr-btn--tertiary-no-outline w-full!"
                      onclick={backToEmail}
                    >
                      Renvoyer un code
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
                    title="Fermer"
                  >
                    Fermer
                    <span aria-hidden="true" class="ml-1">×</span>
                  </button>
                </div>

                <h3 class="text-base! font-bold! mb-2!">Comment mes donnees sont-elles utilisees ?</h3>
                <p class="fr-text--sm mb-6!">
                  Les conversations et les preferences que vous exprimez sur compar:IA sont
                  utilisees de maniere anonyme pour constituer des jeux de donnees representatifs
                  des langues et usages europeens, afin de reduire les biais culturels et proposer
                  de futurs modeles d'IA plus inclusifs.
                </p>

                <h3 class="text-base! font-bold! mb-2!">Les jeux de donnees compar:IA</h3>
                <p class="fr-text--sm mb-2!">
                  Les conversations sont publiees en open data dans des jeux de donnees de
                  recherche. C'est pourquoi nous vous demandons de <strong>ne jamais inclure</strong> dans
                  vos conversations :
                </p>
                <ul class="fr-text--sm mb-4!">
                  <li>votre nom, prenom ou celui d'un tiers</li>
                  <li>des adresses (postale, email)</li>
                  <li>des numeros de telephone</li>
                  <li>des informations medicales, financieres ou juridiques personnell</li>
                  <li>tout autre element permettant de vous identifier</li>
                </ul>
                <p class="fr-text--sm mb-0!">
                  Votre email n'est jamais publie ni partage avec des tiers.
                </p>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>
