<script lang="ts">
  import { Button, Checkbox } from '$components/dsfr'
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import MarkdownInline from '$components/markdown/MarkdownInline.svelte'
  import { getAuthContext } from '$lib/auth.svelte'
  import {
    buildConsentEvidence,
    buildConsentCheckboxLabel,
    getActiveTerms,
    getConsentStatus,
    INITIAL_CONSENT_MODAL_STATE,
    requestConsentModalState,
    resolveConsentModalState,
    storeConsent,
    serverHasCurrentAcceptance,
    CANONICAL_LEGAL_LINKS,
    type ConsentDocument
  } from '$lib/consent'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { tick } from 'svelte'

  const locale = getLocale()
  const auth = getAuthContext()
  let terms = $state<ConsentDocument>()
  const checkboxLabel = $derived(terms ? buildConsentCheckboxLabel(terms) : '')
  let acceptTos = $state(false)
  let modalState = $state({ ...INITIAL_CONSENT_MODAL_STATE })
  const showModal = $derived(modalState.open)
  let savingConsent = $state(false)
  let modal: HTMLDialogElement
  let tosError = $state<string>()
  let statusRequest = 0
  let statusLoad: Promise<void> | undefined
  let pendingAction: (() => unknown | Promise<unknown>) | undefined
  let returnFocus: HTMLElement | null = null

  function getModalController() {
    return (
      window as unknown as Window & {
        dsfr: (element: HTMLElement) => { modal: { disclose: () => void; conceal: () => void } }
      }
    ).dsfr(modal).modal
  }

  async function loadConsentStatus(authenticated: boolean) {
    const request = ++statusRequest
    try {
      const activeTerms = await getActiveTerms(locale)
      const status = await getConsentStatus(authenticated)
      if (request !== statusRequest) return
      terms = activeTerms
      modalState = resolveConsentModalState(activeTerms, status)
      if (serverHasCurrentAcceptance(activeTerms, status)) {
        acceptTos = true
        await tick()
        if (modal) getModalController().conceal()
      } else {
        acceptTos = false
      }
    } catch {
      if (request !== statusRequest) return
      tosError =
        'Les conditions d’utilisation ne peuvent pas être chargées. Réessayez avant de continuer.'
      modalState = { status: 'error', open: false }
    }
  }

  $effect(() => {
    statusLoad = loadConsentStatus(!!auth.user)
  })

  $effect(() => {
    if (acceptTos && terms) tosError = undefined
  })

  export async function runAfterAcceptance(
    action: () => unknown | Promise<unknown>
  ): Promise<void> {
    while (modalState.status === 'loading') {
      await (statusLoad ?? loadConsentStatus(!!auth.user))
    }

    if (modalState.status === 'accepted') {
      await action()
      return
    }

    pendingAction = action
    returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    modalState = requestConsentModalState(modalState)
    await tick()
    if (modal) getModalController().disclose()
  }

  async function cancelPendingAction(): Promise<void> {
    pendingAction = undefined
    acceptTos = false
    modalState = { ...modalState, open: false }
    getModalController().conceal()
    await tick()
    returnFocus?.focus()
    returnFocus = null
  }

  async function acceptAndClose() {
    if (!acceptTos || !terms) {
      tosError = m['home.intro.tos.error']()
      return
    }

    savingConsent = true
    tosError = undefined
    const consent = buildConsentEvidence(terms)
    let action: (() => unknown | Promise<unknown>) | undefined
    try {
      await api.request(auth.user ? '/auth/consent' : '/auth/consent/anonymous', {
        method: 'POST',
        body: JSON.stringify({ consent })
      })
      storeConsent(consent)
      modalState = { status: 'accepted', open: false }
      getModalController().conceal()
      action = pendingAction
      pendingAction = undefined
      returnFocus = null
    } catch {
      tosError = 'Votre choix n’a pas pu être enregistré. Vérifiez votre connexion puis réessayez.'
    } finally {
      savingConsent = false
    }

    await action?.()
  }
</script>

<button class="hidden" data-fr-opened={showModal} aria-controls="fr-modal-welcome"> Hidden </button>
<dialog
  bind:this={modal}
  aria-labelledby="fr-modal-title-modal-welcome"
  id="fr-modal-welcome"
  class="fr-modal"
  data-fr-concealing-backdrop="false"
>
  <div class="fr-container fr-container--fluid fr-container-md">
    <div class="fr-grid-row fr-grid-row--center">
      <div class="fr-col-12 fr-col-md-8 fr-col-lg-6">
        <div class="fr-modal__body rounded-xl">
          <div class="fr-modal__header">
            <button
              class="fr-btn--close fr-btn"
              type="button"
              aria-controls="fr-modal-welcome"
              onclick={cancelPendingAction}>Fermer sans envoyer</button
            >
          </div>
          <div class="fr-modal__content px-7">
            <h2 id="fr-modal-title-modal-welcome" class="fr-modal__title text-primary!">
              <MarkdownInline message={terms?.presentation.arena.title ?? 'Avant de commencer'} />
            </h2>
            {#if terms}
              <div class="fr-text--sm mb-6">
                <Markdown message={terms.presentation.arena.introduction} sanitize_html />
              </div>
            {/if}
            <Checkbox
              bind:checked={acceptTos}
              id="tos-modal"
              label={checkboxLabel}
              links={CANONICAL_LEGAL_LINKS}
              error={tosError}
            />
          </div>
          <div class="fr-modal__footer justify-end">
            <Button disabled={!terms || !acceptTos || savingConsent} onclick={acceptAndClose}>
              <MarkdownInline
                message={savingConsent
                  ? 'Enregistrement…'
                  : (terms?.presentation.arena.buttonLabel ?? 'Confirmer')}
                allowLinks={false}
              />
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>
