<script lang="ts" generics="Option extends { label?: string; value: string }">
  import type { Snippet } from 'svelte'
  import type { ClassValue, HTMLFieldsetAttributes } from 'svelte/elements'

  let {
    id,
    legend,
    options,
    value = $bindable([]),
    row = false,
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
    legendClass?: ClassValue
    labelClass?: ClassValue
    legendSlot?: Snippet<[{ legend: string }]>
    labelSlot?: Snippet<[{ option: Option; index: number }]>
  } & HTMLFieldsetAttributes = $props()
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

  <div class="flex flex-wrap">
    {#each options as option, i (option.value)}
      <div
        class={['fr-fieldset__element not-last:mb-2! last:mb-0!', { 'grow-0! basis-auto!': row }]}
      >
        <div class="fr-checkbox-group">
          <input
            name="checkbox1"
            id={`${id}-${option.value}`}
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
