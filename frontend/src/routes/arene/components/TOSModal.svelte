<script lang="ts">
  import { Button, Checkbox } from '$components/dsfr'
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import MarkdownInline from '$components/markdown/MarkdownInline.svelte'
  import { getAuthContext } from '$lib/auth.svelte'
  import {
    consentCheckboxLabel,
    legalLinks,
    loadConsent,
    reloadConsent,
    submitConsent,
    type ConsentDocument
  } from '$lib/consent'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { onMount, tick } from 'svelte'

  type Action = () => unknown | Promise<unknown>

  const locale = getLocale()
  const auth = getAuthContext()

  let terms = $state<ConsentDocument>()
  let status = $state<'loading' | 'accepted' | 'required' | 'error'>('loading')
  let acceptTos = $state(false)
  let savingConsent = $state(false)
  let tosError = $state<string>()
  let modal: HTMLDialogElement
  let loaded: Promise<void> | undefined
  let pendingAction: Action | undefined
  let returnFocus: HTMLElement | null = null

  const checkboxLabel = $derived(terms ? consentCheckboxLabel(terms) : '')

  function getModalController() {
    return (
      window as unknown as Window & {
        dsfr: (element: HTMLElement) => { modal: { disclose: () => void; conceal: () => void } }
      }
    ).dsfr(modal).modal
  }

  async function readConsent(again = false) {
    status = 'loading'
    tosError = undefined
    try {
      const snapshot = await (again ? reloadConsent : loadConsent)(locale, !!auth.user)
      terms = snapshot.document
      acceptTos = snapshot.accepted
      status = snapshot.accepted ? 'accepted' : 'required'
    } catch {
      terms = undefined
      status = 'error'
      tosError = m['consent.loadFailed']()
    }
  }

  onMount(() => {
    loaded = readConsent()
  })

  $effect(() => {
    if (acceptTos && terms) tosError = undefined
  })

  export async function runAfterAcceptance(action: Action): Promise<void> {
    await loaded
    if (status === 'accepted') {
      await action()
      return
    }

    pendingAction = action
    returnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null
    await tick()
    getModalController().disclose()
  }

  async function retry() {
    loaded = readConsent(true)
    await loaded
    // Accepted in another tab or since the first attempt: nothing left to ask,
    // close and run what was waiting.
    if (status !== 'accepted') return
    getModalController().conceal()
    const action = pendingAction
    pendingAction = undefined
    returnFocus = null
    await action?.()
  }

  async function cancelPendingAction() {
    pendingAction = undefined
    acceptTos = false
    getModalController().conceal()
    await tick()
    returnFocus?.focus()
    returnFocus = null
  }

  async function acceptAndClose() {
    if (!acceptTos || !terms) {
      tosError = m['consent.required']()
      return
    }

    savingConsent = true
    tosError = undefined
    let action: Action | undefined
    try {
      await submitConsent(terms, !!auth.user)
      status = 'accepted'
      getModalController().conceal()
      action = pendingAction
      pendingAction = undefined
      returnFocus = null
    } catch {
      tosError = m['consent.saveFailed']()
    } finally {
      savingConsent = false
    }

    await action?.()
  }
</script>

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
              onclick={cancelPendingAction}>{m['consent.close']()}</button
            >
          </div>
          <div class="fr-modal__content px-7">
            {#if terms}
              <h2 id="fr-modal-title-modal-welcome" class="fr-modal__title text-primary!">
                <MarkdownInline message={terms.presentation.arena.title} />
              </h2>
              <div class="fr-text--sm mb-6">
                <Markdown message={terms.presentation.arena.introduction} sanitize_html />
              </div>
              <Checkbox
                bind:checked={acceptTos}
                id="tos-modal"
                label={checkboxLabel}
                links={legalLinks()}
                error={tosError}
              />
            {:else}
              <h2 id="fr-modal-title-modal-welcome" class="fr-modal__title text-primary!">
                {m['consent.loadFailed']()}
              </h2>
              <p class="fr-error-text" role="alert">{tosError}</p>
            {/if}
          </div>
          <div class="fr-modal__footer justify-end">
            {#if terms}
              <Button disabled={!acceptTos || savingConsent} onclick={acceptAndClose}>
                <MarkdownInline
                  message={savingConsent
                    ? m['consent.saving']()
                    : (terms.presentation.arena.buttonLabel ?? m['consent.confirm']())}
                  allowLinks={false}
                />
              </Button>
            {:else}
              <Button text={m['consent.retry']()} disabled={status === 'loading'} onclick={retry} />
            {/if}
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>
