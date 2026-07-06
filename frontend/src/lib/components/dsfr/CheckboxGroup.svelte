<script lang="ts" generics="Option extends { label?: string; value: string }">
  import type { Snippet } from 'svelte'
  import type { ClassValue, HTMLFieldsetAttributes } from 'svelte/elements'

  let {
    id,
    legend,
    options,
    value = $bindable([]),
    row = false,
    normalizeAllSelection = true,
    legendClass = '',
    labelClass = '',
    legendSlot,
    labelSlot,
    ...props
  }: {
    legend: string
    options: Option[]
    value: string[]
    row?: boolean
    normalizeAllSelection?: boolean
    legendClass?: ClassValue
    labelClass?: ClassValue
    legendSlot?: Snippet<[{ legend: string }]>
    labelSlot?: Snippet<[{ option: Option; index: number }]>
  } & HTMLFieldsetAttributes = $props()

  const all = $derived(options.find((opt) => opt.value === 'all'))
  const opts = $derived(options.filter((opt) => opt.value !== 'all'))

  const allSelected = $derived(
    value.length === options.length || (normalizeAllSelection && value.length === 0)
  )
  const ariaAllSelected = $derived(allSelected ? 'true' : value.length === 0 ? 'false' : 'mixed')

  function toggleAll() {
    if (allSelected) value = []
    else value = options.map((opt) => opt.value)
  }

  $effect(() => {
    if (normalizeAllSelection && allSelected) value = []
  })
</script>

<fieldset
  {...props}
  {id}
  aria-labelledby={`${id}-form-legend`}
  class={['fr-fieldset', props.class]}
>
  <legend
    class={['fr-fieldset__legend--regular fr-fieldset__legend', legendClass]}
    id={`${id}-form-legend`}
  >
    {#if legendSlot}
      {@render legendSlot({ legend })}
    {:else}
      {legend}
    {/if}
  </legend>

  {#if all}
    <div
      class={[
        'fr-fieldset__element mb-2 pb-2 w-full border-b-1 border-[--grey-925-125]',
        { 'grow-0! basis-auto!': row }
      ]}
    >
      <div class="fr-checkbox-group">
        <input
          name="checkbox-{id}"
          id="${id}-all"
          type="checkbox"
          value="all"
          checked={allSelected}
          aria-checked={ariaAllSelected}
          onclick={() => toggleAll()}
          disabled={value.length === 0}
        />
        <label class={['fr-label ms-6!', { 'inline-block!': row }, labelClass]} for="${id}-all">
          {#if labelSlot}
            {@render labelSlot({ option: all, index: -1 })}
          {:else}
            {all.label ?? all.value}
          {/if}
        </label>
      </div>
    </div>
  {/if}

  <div class="flex w-full flex-col">
    {#each opts as option, i (option.value)}
      <div
        class={['fr-fieldset__element not-last:mb-2! last:mb-0!', { 'grow-0! basis-auto!': row }]}
      >
        <div class="fr-checkbox-group">
          <input
            name="checkbox-{id}"
            id="{id}-{option.value}"
            type="checkbox"
            value={option.value}
            bind:group={value}
          />
          <label
            class={['fr-label ms-6!', { 'inline-block!': row }, labelClass]}
            for={`${id}-${option.value}`}
          >
            {#if labelSlot}
              {@render labelSlot({ option, index: i })}
            {:else}
              {option.label ?? option.value}
            {/if}
          </label>
        </div>
      </div>
    {/each}
  </div>
</fieldset>

<style>
  /* Override only light theme blue to purple */
  :root[data-fr-theme='light'] input[type='checkbox'] + label {
    --border-action-high-blue-france: var(--blue-france-main-525);
    --border-active-blue-france: var(--blue-france-main-525);
    --background-active-blue-france: var(--blue-france-main-525);
  }

  /* To avoid flickering at page load */
  @media (prefers-color-scheme: light) {
    :root[data-fr-theme='system'] input[type='checkbox'] + label {
      --border-action-high-blue-france: var(--blue-france-main-525);
      --border-active-blue-france: var(--blue-france-main-525);
      --background-active-blue-france: var(--blue-france-main-525);
    }
  }

  input[type='checkbox'] + label::before {
    position: relative;
    height: 1rem !important;
    width: 1rem !important;
    left: -1.5rem !important;
    top: 0.25rem !important;
  }
</style>
