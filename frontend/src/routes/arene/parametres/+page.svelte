<script lang="ts">
  import { resolve } from '$app/paths'
  import { Button, Input, Link, Modal, Tabs } from '$components/dsfr'
  import SeoHead from '$components/SEOHead.svelte'
  import ThemeSelector from '$components/ThemeSelector.svelte'
  import { getAuthContext, logout } from '$lib/auth.svelte'
  import { getComparisonsContext } from '$lib/chatService.svelte'
  import { withdrawLocalConsent } from '$lib/consent'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'

  const auth = getAuthContext()
  const comparisons = getComparisonsContext()
  const tabs = [
    { id: 'account', label: 'Compte' },
    { id: 'about', label: 'À propos' }
  ] as const

  let eraseEmail = $state('')
  let erasingAccount = $state(false)
  let eraseError = $state('')

  function exportData() {
    if (!auth.user) return

    const content = JSON.stringify(
      {
        exported_at: new Date().toISOString(),
        account: { email: auth.user.email },
        conversations: comparisons
      },
      null,
      2
    )
    const url = URL.createObjectURL(new Blob([content], { type: 'application/json' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `comparia-donnees-${new Date().toISOString().slice(0, 10)}.json`
    anchor.click()
    URL.revokeObjectURL(url)
  }

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

<header class="bg-very-light-primary px-4 py-4 shadow-sm">
  <div class="fr-container max-w-[1000px]">
    <h1 class="fr-h5 mb-0!">Paramètres</h1>
    <p class="fr-text--sm text-grey mb-0!">Compte, données et informations sur la plateforme</p>
  </div>
</header>

<div class="py-6 lg:py-8">
  <div class="fr-container max-w-[1000px]">
    <Tabs {tabs} label="Rubriques des paramètres" noBorders kind="nav">
      {#snippet tab(tab)}
        {#if tab.id === 'account'}
          <div class="fr-grid-row fr-grid-row--gutters">
            <section class="fr-col-12 fr-col-lg-6" aria-labelledby="account-settings-title">
              <h2 id="account-settings-title" class="fr-h4">Mon compte</h2>

              {#if auth.user}
                <Input
                  id="account-email"
                  type="email"
                  value={auth.user.email}
                  label="Adresse électronique"
                  disabled
                />
                <div class="gap-3 flex flex-wrap">
                  <Button
                    variant="secondary"
                    text="Se déconnecter"
                    icon="logout-box-r-line"
                    onclick={() => logout(auth, comparisons)}
                  />
                  <Button
                    variant="tertiary"
                    text="Supprimer mon compte"
                    class="text-error!"
                    aria-controls="account-erasure-modal"
                    data-fr-opened="false"
                  />
                </div>
              {:else}
                <p>Connectez-vous pour accéder aux paramètres de votre compte.</p>
              {/if}
            </section>

            <section class="fr-col-12 fr-col-lg-6" aria-labelledby="display-settings-title">
              <h2 id="display-settings-title" class="fr-h4">Préférences</h2>
              <p class="fr-text--sm text-grey">Adaptez l’affichage à vos préférences.</p>
              <ThemeSelector />
            </section>
          </div>

          {#if auth.user}
            <section class="fr-mt-8v" aria-labelledby="export-data-title">
              <h2 id="export-data-title" class="fr-h4">Exporter mes données</h2>
              <p class="fr-text--sm text-grey">
                Téléchargez une copie de vos conversations et de vos votes au format JSON.
              </p>
              <Button variant="secondary" text="Exporter mes données" onclick={exportData} />
            </section>
          {/if}
        {:else}
          <section aria-labelledby="useful-links-title">
            <h2 id="useful-links-title" class="fr-h4">Liens utiles</h2>
            <p class="fr-text--sm text-grey max-w-[800px]">
              Sauf mention explicite de propriété intellectuelle détenue par des tiers, les contenus
              de ce site sont proposés sous
              <a href="https://www.etalab.gouv.fr/licence-ouverte-open-licence/">
                licence Etalab 2.0
              </a>.
            </p>
            <ul class="fr-raw-list gap-3 flex flex-col items-start">
              <li><Link href={resolve('/mentions-legales')} text="Mentions légales" /></li>
              <li>
                <Link
                  href={resolve('/arene/modalites')}
                  text="Conditions générales d’utilisation"
                />
              </li>
              <li>
                <Link
                  href={resolve('/arene/donnees-personnelles')}
                  text="Politique de confidentialité"
                />
              </li>
              <li><Link href={resolve('/accessibilite')} text="Accessibilité" /></li>
              <li><Link href={resolve('/ecoconception')} text="Écoconception" /></li>
              <li><Link href="https://github.com/betagouv/ComparIA" text="Code source" /></li>
            </ul>
          </section>
        {/if}
      {/snippet}
    </Tabs>
  </div>
</div>

<Modal
  id="account-erasure-modal"
  titleId="account-erasure-title"
  sizeClass="fr-col-12 fr-col-md-8 fr-col-lg-5"
>
  <h2 id="account-erasure-title" class="fr-modal__title">Supprimer le compte</h2>
  <p>
    La suppression est irréversible. Vos sessions seront révoquées, votre adresse électronique sera
    anonymisée et vos conversations seront détachées du compte.
  </p>
  {#if auth.user}
    <Input
      id="account-erasure-email"
      type="email"
      bind:value={eraseEmail}
      label="Confirmez votre adresse électronique"
      help={`Saisissez ${auth.user.email} pour confirmer la suppression.`}
      error={eraseError}
      autocomplete="email"
    />
  {/if}
  <div class="fr-btns-group fr-btns-group--inline-reverse fr-btns-group--inline-lg">
    <Button
      text={erasingAccount ? 'Suppression…' : 'Supprimer mon compte'}
      disabled={erasingAccount ||
        !auth.user ||
        eraseEmail.trim().toLowerCase() !== auth.user.email.toLowerCase()}
      onclick={eraseAccount}
    />
    <Button variant="secondary" text="Annuler" aria-controls="account-erasure-modal" />
  </div>
</Modal>
