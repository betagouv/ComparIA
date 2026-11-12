<script lang="ts">
  import Dropdown from '$components/Dropdown.svelte'
  import ToolCard from '$components/ToolCard.svelte'
  import { Button, Icon, Modal } from '$components/dsfr'
  import Link from '$components/dsfr/Link.svelte'
  import { FormToggle } from '$components/form'
  import type { ToolPublic } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import { fromEntries, getKeys } from '$lib/utils/commons'

  export type ToolPickerProps = {
    tools: ToolPublic[]
    selected: string[]
    /** The mode turns these tools on itself: shown, not offered. */
    locked?: boolean
    disabled?: boolean
  }

  let {
    tools,
    selected = $bindable(),
    locked = false,
    disabled = false
  }: ToolPickerProps = $props()

  const modalId = 'fr-modal-tools'

  // Starts over when another mode offers other tools, or picked them already.
  let form = $derived.by(() => {
    const toggles = $state(resetForm())
    return toggles
  })
  let applied = $state(false)

  function resetForm() {
    return fromEntries(tools.map((tool) => [tool.key, selected.includes(tool.key)]))
  }

  function applySelected(close?: () => void) {
    selected = getKeys(form).filter((k) => form[k]) as string[]
    applied = true
    close?.()
  }

  function onClose() {
    if (!applied) {
      form = resetForm()
    }
    applied = false
  }
</script>

{#snippet toolToggle(tool: ToolPublic, kind: 'dropdown' | 'modal' = 'dropdown')}
  <FormToggle
    id="tool-{tool.key}-{kind}"
    bind:value={form[tool.key]}
    label={tool.label}
    checkKind="none"
    class="my-2!"
  >
    {#snippet labelSnippet()}
      <ToolCard {tool} />
    {/snippet}
  </FormToggle>
{/snippet}

{#if locked && tools.length > 0}
  <div
    class="cg-border rounded-lg px-3 py-2 text-sm gap-2 md:w-auto bg-white flex w-full items-center border-dashed!"
  >
    <Icon icon="i-ri-lock-line" size="sm" class="text-primary" />
    <span>
      <strong>{tools.map((tool) => tool.label).join(', ')}</strong>
      <span class="text-[--text-mention-grey]">· {m['arenaHome.tools.forced']()}</span>
    </span>
  </div>
{:else if tools.length > 0}
  <Dropdown
    id="dropdown-tools"
    label={m['arenaHome.tools.label']()}
    variant="light"
    {disabled}
    {onClose}
    buttonClass="fr-select text-sm! ps-3! cg-border shadow-none! rounded-lg! md:w-auto! w-full!"
  >
    {#snippet buttonLabel(label)}
      <Icon icon="i-ri-add-large-line" size="sm" class="text-primary me-2" />
      {label}
      <span
        class="ms-1 bg-primary text-white px-2 text-xs inline-block rounded-full py-[3px] align-top"
      >
        {selected.length}
      </span>
    {/snippet}

    {#snippet contentSnippet(close)}
      <ul class="m-0 px-3 py-1 flex list-none flex-col">
        {#each tools.slice(0, 6) as tool (tool.key)}
          <li class="b-b m-0! p-0! border-[--grey-925-125]">
            {@render toolToggle(tool)}
          </li>
        {/each}
      </ul>

      <div class="p-3 gap-3 bottom-0 sticky flex justify-end">
        <Link
          text={m['arenaHome.tools.viewAll']()}
          href="#"
          size="sm"
          aria-controls={modalId}
          data-fr-opened="false"
          onclick={() => applySelected(close)}
          class="h-fit place-self-center"
        />

        <Button
          variant="primary"
          size="sm"
          text={m['arenaHome.tools.add']()}
          {disabled}
          title={disabled ? m['arenaHome.tools.locked']() : undefined}
          onclick={() => applySelected(close)}
        />
      </div>
    {/snippet}
  </Dropdown>

  <Modal
    id={modalId}
    titleId="{modalId}-title"
    sizeClass="fr-col-12 fr-col-md-10"
    class="tools-modal"
    contentClass="mb-8! px-6! md:px-12!"
    {onClose}
  >
    <h2 id="{modalId}-title" class="fr-h6 mb-0!">{m['arenaHome.tools.label']()}</h2>

    <p class="fr-text--sm mb-4! text-[--text-mention-grey]">
      {m['arenaHome.tools.contract']()}
    </p>

    <ul class="p-0! md:grid-cols-2 gap-2 md:gap-4 grid list-none">
      {#each tools as tool (tool.key)}
        <li class="p-0">
          {@render toolToggle(tool, 'modal')}
        </li>
      {/each}
    </ul>

    {#snippet footer()}
      <div class="gap-4 md:flex-row flex w-full flex-col-reverse">
        <Button
          text={m['words.cancel']()}
          variant="tertiary"
          aria-controls={modalId}
          class="md:w-auto! w-full!"
        />
        <div class="gap-4 md:order-none md:ms-auto order-1 flex">
          <div
            class="text-sm place-self-center whitespace-nowrap text-[--text-mention-grey]"
            aria-live="polite"
          >
            {selected.length === 0
              ? m['arenaHome.tools.none']()
              : m['arenaHome.tools.count']({ count: selected.length })}
          </div>
          {#if selected.length > 0}
            <Button
              variant="tertiary"
              text={m['arenaHome.tools.clear']()}
              onclick={() => (selected = [])}
              class="md:w-auto! w-full!"
            />
          {/if}
        </div>
        <Button
          text={m['arenaHome.tools.add']()}
          aria-controls={modalId}
          onclick={() => applySelected()}
          class="md:w-auto! w-full!"
        />
      </div>
    {/snippet}
  </Modal>
{/if}
