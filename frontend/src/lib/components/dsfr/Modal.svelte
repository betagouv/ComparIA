<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { ClassValue, HTMLDialogAttributes } from 'svelte/elements'
  import { Button } from '.'

  let {
    id,
    titleId,
    sizeClass = 'fr-col-12 fr-col-md-8 fr-col-lg-6',
    contentClass,
    headerClass,
    onClose,
    children
  }: {
    id: string
    titleId: string
    sizeClass?: string
    contentClass?: ClassValue
    headerClass?: ClassValue
    onClose?: () => void
  } & HTMLDialogAttributes = $props()

  // DSFR announces a real close with this event, the same way ModelInfoModal
  // listens for it. Blur is not a close: focusing a field inside the modal
  // blurs the dialog, and reporting that as a close made consumers act on a
  // modal the visitor was still using.
  const dsfrEvents = { 'ondsfr.conceal': () => onClose?.() }
</script>

<dialog aria-labelledby={titleId} {id} class="fr-modal" {...dsfrEvents}>
  <div class="fr-container fr-container--fluid fr-container-md">
    <div class="fr-grid-row fr-grid-row--center">
      <div class={sizeClass}>
        <div class="fr-modal__body rounded-xl relative">
          <div class={['fr-modal__header pb-0!', headerClass]}>
            <Button
              variant="tertiary-no-outline"
              text={m['words.close']()}
              title={m['closeModal']()}
              aria-controls={id}
              class="fr-btn--close z-100"
            />
          </div>

          <div class={['fr-modal__content', contentClass]}>
            {@render children?.()}
          </div>
        </div>
      </div>
    </div>
  </div>
</dialog>
