<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { HTMLDialogAttributes } from 'svelte/elements'
  import { Button } from '.'

  let {
    id,
    titleId,
    sizeClass = 'fr-col-12 fr-col-md-8 fr-col-lg-6',
    onClose,
    children
  }: {
    id: string
    titleId: string
    sizeClass?: string
    onClose?: () => void
  } & HTMLDialogAttributes = $props()
</script>

<dialog
  aria-labelledby={titleId}
  {id}
  class="fr-modal"
  onblur={() => onClose?.()}
  onkeydown={(e) => {
    if (e.key === 'Escape') onClose?.()
  }}
>
  <div class="fr-container fr-container--fluid fr-container-md">
    <div class="fr-grid-row fr-grid-row--center">
      <div class={sizeClass}>
        <div class="fr-modal__body rounded-xl">
          <div class="fr-modal__header pb-0!">
            <Button
              variant="tertiary-no-outline"
              text={m['words.close']()}
              title={m['closeModal']()}
              aria-controls={id}
              class="fr-btn--close"
              onclick={() => onClose?.()}
            />
          </div>

          <div class="fr-modal__content">
            {@render children?.()}
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>
