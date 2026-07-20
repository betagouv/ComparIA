<script lang="ts">
  import { Button, Input } from '$components/dsfr'
  import SeoHead from '$components/SEOHead.svelte'
  import { getAuthContext } from '$lib/auth.svelte'
  import { withdrawLocalConsent } from '$lib/consent'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'

  const auth = getAuthContext()
  let eraseEmail = $state('')
  let erasingAccount = $state(false)
  let eraseError = $state('')

  async function eraseAccount() {
    if (!auth.user || eraseEmail.trim().toLowerCase() !== auth.user.email.toLowerCase()) {
      eraseError = 'Saisissez exactement l’adresse électronique de votre compte.'
      return
    }

    erasingAccount = true
    eraseError = ''
    try {
      await api.request('/auth/me', {
        method: 'DELETE',
        body: JSON.stringify({ email: eraseEmail.trim() })
      })
      withdrawLocalConsent()
      auth.user = null
      window.location.href = '/arene'
    } catch {
      eraseError =
        'Le compte n’a pas pu être supprimé. Réessayez ou contactez l’équipe pour exercer ce droit.'
    } finally {
      erasingAccount = false
    }
  }
</script>

<SeoHead title={m['seo.titles.settings']()} />

<main class="py-10 lg:py-15">
  <div class="fr-container max-w-[900px]">
    <h1>Paramètres</h1>

    <section aria-labelledby="account-settings-title">
      <h2 id="account-settings-title">Compte</h2>

      {#if auth.user}
        <div class="fr-callout fr-callout--brown-caramel">
          <h3 class="fr-callout__title">Supprimer mon compte</h3>
          <p class="fr-callout__text">
            Cette action révoque les sessions, anonymise l’adresse électronique et détache les
            conversations du compte. Elle est irréversible.
          </p>
          <Input
            id="account-erasure-email"
            type="email"
            bind:value={eraseEmail}
            label="Confirmez votre adresse électronique"
            help={`Saisissez ${auth.user.email} pour confirmer la suppression.`}
            error={eraseError}
            autocomplete="email"
          />
          <Button
            variant="secondary"
            text={erasingAccount ? 'Suppression…' : 'Supprimer définitivement mon compte'}
            disabled={erasingAccount ||
              eraseEmail.trim().toLowerCase() !== auth.user.email.toLowerCase()}
            onclick={eraseAccount}
          />
        </div>
      {:else}
        <p>Connectez-vous pour accéder aux paramètres de votre compte.</p>
      {/if}
    </section>
  </div>
</main>
