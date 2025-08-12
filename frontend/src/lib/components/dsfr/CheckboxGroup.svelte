<script lang="ts" generics="Option extends { label?: string; value: string }">
  import type { Snippet } from 'svelte'
  import type { ClassValue, HTMLFieldsetAttributes } from 'svelte/elements'

  let {
    id,
    legend,
    options,
    value = $bindable([]),
    legendClass = '',
    labelClass = '',
    labelSlot,
    ...props
  }: {
    legend: string
    options: Option[]
    value: string[]
    legendClass?: ClassValue
    labelClass?: ClassValue
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
    {legend}
  </legend>

  {#each options as option, i}
    <div class="fr-fieldset__element">
      <div class="fr-checkbox-group">
        <input
          name="checkbox1"
          id={`${id}-${option.value}`}
          type="checkbox"
          value={option.value}
          bind:group={value}
        />
        <label class={['fr-label', labelClass]} for={`${id}-${option.value}`}>
          {#if labelSlot}
            {@render labelSlot({ option, index: i })}
          {:else}
            {option.label ?? option.value}
          {/if}
        </label>
      </div>
    </div>
  {/each}
</fieldset>
