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

  // Reads as a count once past a single tool: the labels are too long to list.
  const triggerLabel = $derived(
    selected.length === 0
      ? m['arenaHome.tools.none']()
      : selected.length === 1
        ? (tools.find((tool) => tool.key === selected[0])?.label ?? m['arenaHome.tools.label']())
        : m['arenaHome.tools.count']({ count: selected.length })
  )
</script>

{#if tools.length > 0}
  <div class="my-auto grow">
    <Button
      variant="tertiary"
      aria-controls={modalId}
      data-fr-opened="false"
      {disabled}
      title={disabled ? m['arenaHome.tools.locked']() : undefined}
      class="w-full! justify-between"
    >
      <span class="gap-2 flex items-center">
        <Icon icon="i-ri-tools-line" size="sm" class="text-primary" />
        {triggerLabel}
      </span>
      <Icon icon="i-ri-arrow-down-s-line" size="sm" />
    </Button>
  </div>

  <Modal id={modalId} titleId="{modalId}-title">
    <h2 id="{modalId}-title" class="text-xl!">{m['arenaHome.tools.label']()}</h2>

    <fieldset class="fr-fieldset p-0! m-0! border-0!">
      <legend class="fr-fieldset__legend text-sm! text-[--text-mention-grey]">
        {m['arenaHome.tools.legend']()}
      </legend>
      {#each tools as tool (tool.key)}
        <div class="fr-checkbox-group fr-checkbox-group--sm">
          <input id="tool-{tool.key}" type="checkbox" value={tool.key} bind:group={selected} />
          <label class="fr-label" for="tool-{tool.key}">
            {tool.label}
            {#if tool.description}
              <span class="fr-hint-text">{tool.description}</span>
            {/if}
          </label>
        </div>
      {/each}
    </fieldset>

    <p class="fr-text--sm mb-0! text-[--text-mention-grey]">
      {m['arenaHome.tools.contract']()}
    </p>
  </Modal>
{/if}
