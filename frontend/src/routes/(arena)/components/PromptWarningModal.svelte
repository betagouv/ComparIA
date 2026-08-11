<script lang="ts">
  import { Button, Modal } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'

  let {
    warnings,
    onProceed,
    onEdit
  }: {
    warnings?: string[]
    onProceed?: () => void
    onEdit?: () => void
  } = $props()

  const modalId = 'fr-modal-prompt-warning'
</script>

<button class="hidden" data-fr-opened={!!warnings?.length} aria-controls={modalId}>Hidden</button>

<Modal
  id={modalId}
  titleId="{modalId}-title"
  onClose={() => onEdit?.()}
  headerClass="pb-0!"
  contentClass="mt-0! mb-0! pb-6!"
>
  <h2 id="{modalId}-title" class="fr-modal__title">
    {m['arene.promptWarning.title']()}
  </h2>

  {#each warnings ?? [] as warning, index (index)}
    <p>{warning}</p>
  {/each}

  <div class="fr-btns-group fr-btns-group--inline-md mb-0!">
    <Button
      variant="secondary"
      text={m['arene.promptWarning.edit']()}
      aria-controls={modalId}
      onclick={() => onEdit?.()}
    />
    <!-- No aria-controls: DSFR would close the modal on its own listener, and
         the close reaches onClose, and so onEdit, before this handler runs.
         onEdit drops the pending request, which onProceed needs to send it.
         Sending clears the warnings, which closes the modal anyway. -->
    <Button text={m['arene.promptWarning.proceed']()} onclick={() => onProceed?.()} />
  </div>
</Modal>

<style lang="postcss">
  :global(#fr-modal-prompt-warning.fr-modal) {
    background-color: rgb(22 22 22 / 48%);
    justify-content: center;
    padding-block: 1rem;
  }

  :global(#fr-modal-prompt-warning .fr-container) {
    margin-block: auto;
  }

  :global(#fr-modal-prompt-warning.fr-modal::before),
  :global(#fr-modal-prompt-warning.fr-modal::after) {
    content: none;
  }
</style>
