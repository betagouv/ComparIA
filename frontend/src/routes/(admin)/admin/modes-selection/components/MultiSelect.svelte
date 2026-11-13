<script lang="ts">
  import Dropdown from '$components/Dropdown.svelte'
  import { Button, Checkbox } from '$components/dsfr'
  import { FormField } from '$components/form'
  import { m } from '$lib/i18n/messages'

  type Choice = { value: string; label: string; hint?: string }

  let {
    id,
    label,
    help,
    choices,
    value = $bindable(),
    disabled = false,
    errors
  }: {
    id: string
    label: string
    help?: string
    choices: Choice[]
    value?: string[]
    disabled?: boolean
    errors?: Record<string, string>
  } = $props()

  let query = $state('')
  const selected = $derived(value ?? [])

  function normalize(text: string) {
    return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
  }

  // An id saved in the filter whose item has since gone still shows, so it
  // can be unticked.
  const listed: Choice[] = $derived([
    ...choices,
    ...selected
      .filter((itemId) => !choices.some((choice) => choice.value === itemId))
      .map((itemId) => ({ value: itemId, label: m['admin.selectionModes.unknownItem']() }))
  ])

  const shown = $derived.by(() => {
    const words = normalize(query).split(/\s+/).filter(Boolean)
    if (!words.length) return listed
    return listed.filter((choice) => {
      const text = normalize(`${choice.label} ${choice.hint ?? ''}`)
      return words.every((word) => text.includes(word))
    })
  })

  function toggle(itemId: string, checked: boolean) {
    const others = selected.filter((other) => other !== itemId)
    value = checked ? [...others, itemId] : others
  }
</script>

<div class="multi-select mb-6">
  <FormField {id} {label} {help} {errors} component="select">
    {#snippet formItem(fieldProps)}
      <!-- Named by its own text, which says how many are ticked; the label
           above still points at it. -->
      <Dropdown
        id="{id}-menu"
        {label}
        {disabled}
        buttonClass="fr-select mt-2 text-left"
        buttonProps={{
          id: fieldProps.id,
          'aria-labelledby': fieldProps.id,
          'aria-describedby': fieldProps['aria-describedby'],
          'aria-invalid': fieldProps['aria-invalid']
        }}
        maxHeight={360}
        onClose={() => (query = '')}
        class="w-[min(28rem,calc(100vw-2rem))]"
      >
        {#snippet buttonLabel()}
          <span class="sr-only">{label} :</span>
          {selected.length
            ? m['admin.selectionModes.multi.selected']({ count: selected.length })
            : m['admin.selectionModes.multi.none']()}
        {/snippet}
        {#snippet contentSnippet()}
          <div class="p-3 bg-white top-0 sticky z-1 border-b border-[--border-default-grey]">
            <label class="fr-sr-only" for="{id}-search">
              {m['admin.selectionModes.multi.search']({ label })}
            </label>
            <input
              id="{id}-search"
              type="search"
              class="fr-input"
              autocomplete="off"
              placeholder={m['admin.selectionModes.multi.searchPlaceholder']()}
              bind:value={query}
            />
          </div>
          <div class="px-3 pt-3" role="group" aria-label={label}>
            {#each shown as choice (choice.value)}
              <Checkbox
                id="{id}-{choice.value}"
                label={choice.label}
                help={choice.hint}
                class="mb-2!"
                bind:checked={
                  () => selected.includes(choice.value), (checked) => toggle(choice.value, checked)
                }
              />
            {:else}
              <p class="fr-text--sm mb-3! text-[--text-mention-grey]">
                {m['admin.selectionModes.multi.noMatch']()}
              </p>
            {/each}
          </div>
          {#if selected.length}
            <div class="px-3 pb-3 bg-white bottom-0 sticky">
              <Button
                size="sm"
                variant="tertiary-no-outline"
                icon="close-circle-line"
                text={m['admin.selectionModes.multi.clear']()}
                onclick={() => (value = [])}
              />
            </div>
          {/if}
        {/snippet}
      </Dropdown>
    {/snippet}
  </FormField>
</div>

<style>
  .multi-select :global(.dropdown) {
    display: block;
  }
</style>
