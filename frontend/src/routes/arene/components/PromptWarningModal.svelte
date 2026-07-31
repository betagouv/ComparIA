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

<Modal id={modalId} titleId="{modalId}-title" onClose={() => onEdit?.()}>
  <h2 id="{modalId}-title" class="fr-modal__title text-primary!">
    <Icon icon="i-ri-error-warning-line" block size="lg" class="text-primary me-2" />
    {m['arene.promptWarning.title']()}
  </h2>

  {#each warnings ?? [] as warning, index (index)}
    <p class="text-[14px]!">{warning}</p>
  {/each}

  <div class="gap-3 md:flex-row flex flex-col justify-end">
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
