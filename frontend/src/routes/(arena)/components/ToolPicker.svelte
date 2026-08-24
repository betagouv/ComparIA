<script lang="ts">
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

    <ul class="fr-tags-group mb-6!">
      {#each tools as tool (tool.key)}
        <li>
          <button
            type="button"
            class={[
              'tool-pill fr-tag gap-2 bg-white! px-4! py-2! text-base! rounded-full! border-2! border-solid!',
              selected.includes(tool.key)
                ? 'border-primary! text-primary!'
                : 'text-dark-grey! border-[--border-default-grey]!'
            ]}
            aria-pressed={selected.includes(tool.key)}
            aria-describedby={tool.description ? `tool-${tool.key}-description` : undefined}
            onclick={() => toggleTool(tool.key)}
          >
            <Icon icon="i-ri-tools-line" size="sm" />
            {tool.label}
          </button>
          {#if tool.description}
            <span id="tool-{tool.key}-description" class="fr-sr-only">{tool.description}</span>
          {/if}
        </li>
      {/each}
    </ul>

    <p class="fr-text--sm mb-0! text-[--text-mention-grey]">
      {m['arenaHome.tools.contract']()}
    </p>
  </Modal>
{/if}

<style>
  :global(.tools-modal.fr-modal) {
    background-color: rgba(22, 22, 22, 0.2);
  }

  :global(.tools-modal .tool-pill[aria-pressed='true']) {
    color: var(--text-action-high-blue-france);
    background-color: var(--background-lifted-grey) !important;
    background-image: none !important;
    border-color: var(--blue-france-main-525) !important;
    animation: tool-pill-select 160ms ease-out;
  }

  :global(.tools-modal .tool-pill[aria-pressed='true']::after) {
    display: none;
    content: none;
  }

  @keyframes tool-pill-select {
    from {
      transform: scale(0.97);
    }

    to {
      transform: scale(1);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    :global(.tools-modal .tool-pill[aria-pressed='true']) {
      animation: none;
    }
  }
</style>
