<script lang="ts">
  import { Icon } from '$components/dsfr'
  import { useLocalStorage } from '$lib/helpers/useLocalStorage.svelte'
  import { m } from '$lib/i18n/messages'

  const visited = useLocalStorage('comparia:visited', false)
  const pratices = [
    { label: 'welcome.errors', icon: 'success-line' },
    { label: 'welcome.privacy', icon: 'pass-expired-line' },
    { label: 'welcome.use', icon: 'chat-delete-line' }
  ] as const

  function onClose() {
    visited.value = true
  }
</script>

<button class="hidden" data-fr-opened={!visited.value} aria-controls="fr-modal-welcome">
  Hidden
</button>
<dialog
  aria-labelledby="fr-modal-title-modal-welcome"
  role="dialog"
  id="fr-modal-welcome"
  class="fr-modal"
  data-fr-concealing-backdrop="false"
>
  <div class="fr-container fr-container--fluid fr-container-md">
    <div class="fr-grid-row fr-grid-row--center">
      <div class="fr-col-12 fr-col-md-8 fr-col-lg-6">
        <div class="fr-modal__body">
          <div class="fr-modal__header">
            <button
              class="fr-btn--close fr-btn"
              title="Fermer la fenêtre modale"
              aria-controls="fr-modal-welcome"
              id="fr-modal-welcome-close"
              onclick={onClose}
            >
              {m['words.close']()}
            </button>
          </div>
          <div class="fr-modal__content">
            <h1 id="fr-modal-title-modal-welcome" class="fr-modal__title">
              {m['welcome.title']()}
            </h1>

            <p><strong>{m['welcome.goodPractices']()}</strong></p>

            {#each pratices as { label, icon }}
              <div class="mb-4 flex">
                <Icon {icon} block class="text-primary me-2" />
                <p class="mb-0!">{m[label]()}</p>
              </div>
            {/each}
          </div>
          <div class="fr-modal__footer">
            <div
              class="fr-btns-group fr-btns-group--right fr-btns-group--inline-reverse fr-btns-group--inline-lg fr-btns-group--icon-left"
            >
              <button
                class="fr-btn purple-btn"
                data-fr-opened="false"
                aria-controls="fr-modal-welcome"
                onclick={onClose}
              >
                {m['welcome.go']()}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>
