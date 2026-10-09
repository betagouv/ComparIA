<script lang="ts">
  import ToolCard from '$components/ToolCard.svelte'
  import { Button, Icon, Modal } from '$components/dsfr'
  import type { ToolPublic } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'

  export type ToolPickerProps = {
    tools: ToolPublic[]
    selected: string[]
    disabled?: boolean
  }

  let { tools, selected = $bindable(), disabled = false }: ToolPickerProps = $props()

  const modalId = 'fr-modal-tools'

  // Keep the trigger stable and compact as more tools become available.
  const triggerLabel = $derived(
    selected.length === 0
      ? m['arenaHome.tools.none']()
      : `${m['arenaHome.tools.label']()} (${selected.length})`
  )

  function toggleTool(key: string): void {
    selected = selected.includes(key)
      ? selected.filter((selectedKey) => selectedKey !== key)
      : [...selected, key]
  }
</script>

{#if tools.length > 0}
  <div class="min-w-0 md:w-auto my-auto w-full">
    <Button
      variant="secondary"
      native
      aria-controls={modalId}
      data-fr-opened="false"
      {disabled}
      title={disabled ? m['arenaHome.tools.locked']() : undefined}
      class="bg-white! px-3! text-sm! text-dark-grey! md:w-auto! md:max-w-[240px] w-full! max-w-full! items-center justify-start"
      style="--border-action-high-blue-france: var(--grey-925-125)"
    >
      <span class="gap-2 min-w-0 flex items-center">
        <Icon icon="i-ri-tools-line" size="sm" class="text-primary shrink-0" />
        <span class="truncate">{triggerLabel}</span>
      </span>
      <Icon icon="i-ri-arrow-down-s-line" size="sm" class="md:ms-2 ms-auto shrink-0" />
    </Button>
  </div>

  <Modal
    id={modalId}
    titleId="{modalId}-title"
    sizeClass="fr-col-12 fr-col-md-8"
    class="tools-modal"
    contentClass="mb-8! px-6! md:px-12!"
  >
    <h2 id="{modalId}-title" class="fr-h4 mb-6!">{m['arenaHome.tools.label']()}</h2>

    <p class="fr-text--sm mb-6! text-[--text-mention-grey]">
      {m['arenaHome.tools.contract']()}
    </p>

    <!-- DSFR's tag styles are not loaded, so the list is laid out here. -->
    <ul class="m-0 gap-3 p-0 md:grid-cols-2 grid list-none">
      {#each tools as tool (tool.key)}
        {@const pressed = selected.includes(tool.key)}
        <li class="p-0">
          <ToolCard
            id={tool.key}
            label={tool.label}
            description={tool.description}
            {pressed}
            onclick={() => toggleTool(tool.key)}
          />
        </li>
      {/each}
    </ul>

    <div class="mt-8 gap-4 flex flex-wrap items-center justify-between">
      <span class="fr-text--sm mb-0! text-[--text-mention-grey]" aria-live="polite">
        {selected.length === 0
          ? m['arenaHome.tools.none']()
          : m['arenaHome.tools.count']({ count: selected.length })}
      </span>
      <span class="gap-2 flex">
        {#if selected.length > 0}
          <Button
            variant="tertiary-no-outline"
            text={m['arenaHome.tools.clear']()}
            onclick={() => (selected = [])}
          />
        {/if}
        <Button text={m['words.validate']()} aria-controls={modalId} />
      </span>
    </div>
  </Modal>
{/if}

<style>
  :global(.tools-modal.fr-modal) {
    background-color: rgba(22, 22, 22, 0.2);
  }
</style>
