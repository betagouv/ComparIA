<script lang="ts">
  import { Button, Icon, Modal } from '$components/dsfr'
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
  headerClass="pb-0! pt-4! min-h-0!"
  contentClass="pt-0! pb-6! mb-0!"
>
  <span class="warning-badge -mt-9 mb-6 flex items-center justify-center">
    <Icon icon="i-ri-error-warning-line" size="lg" aria-hidden="true" />
  </span>

  <h2 id="{modalId}-title" class="fr-modal__title mb-3! text-dark-grey">
    {m['arene.promptWarning.title']()}
  </h2>

  {#each warnings ?? [] as warning, index (index)}
    <p class="mb-0! text-grey text-[15px]!">{warning}</p>
  {/each}

  <div class="gap-3 mt-6 md:flex-row flex flex-col justify-end">
    <Button
      variant="secondary"
      text={m['arene.promptWarning.edit']()}
      aria-controls={modalId}
      onclick={() => onEdit?.()}
    />
    <Button
      text={m['arene.promptWarning.proceed']()}
      aria-controls={modalId}
      onclick={() => onProceed?.()}
    />
  </div>
</Modal>

<style lang="postcss">
  /* Un avertissement, pas une action de marque : le violet est réservé à ce sur
     quoi on clique. */
  .warning-badge {
    width: 2.75rem;
    height: 2.75rem;
    border-radius: 999px;
    color: var(--warning-425-625);
    background: color-mix(in srgb, var(--warning-425-625) 12%, transparent);
  }
</style>
