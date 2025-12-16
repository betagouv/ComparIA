<script lang="ts" generics="Value extends string, Option extends { value: Value, label: string }">
  import type { ClassValue, HTMLFieldsetAttributes } from 'svelte/elements'

  let {
    id,
    legend,
    options,
    value = $bindable(),
    legendClass = '',
    labelClass = '',
    hideLegend = false,
    size = 'md',
    ...props
  }: {
    legend: string
    options: Option[]
    value: Value
    legendClass?: ClassValue
    labelClass?: ClassValue
    hideLegend?: boolean
    size?: 'sm' | 'md'
  } & HTMLFieldsetAttributes = $props()
</script>

<fieldset
  {...props}
  {id}
  class={[
    'fr-segmented',
    { 'fr-segmented--no-legend': hideLegend, 'fr-segmented--sm': size === 'sm' },
    props.class
  ]}
>
  <legend class={['fr-segmented__legend', legendClass]}>{legend}</legend>

  <div class="fr-segmented__elements">
    {#each options as option (option.value)}
      <div class="fr-segmented__element">
        <input
          name={id}
          id={`${id}-${option.value}`}
          type="radio"
          value={option.value}
          bind:group={value}
        />
        <label class={['fr-label', labelClass]} for={`${id}-${option.value}`}>
          {option.label ?? option.value}
        </label>
      </div>
    {/each}
  </div>
</fieldset>

<style lang="postcss">
  /* Override only light theme blue to purple */
  :root[data-fr-theme='light'] label {
    --border-active-blue-france: var(--blue-france-main-525);
    --text-active-blue-france: var(--blue-france-main-525);
  }

  /* To avoid flickering at page load */
  @media (prefers-color-scheme: light) {
    :root[data-fr-theme='system'] label {
      --border-active-blue-france: var(--blue-france-main-525);
      --text-active-blue-france: var(--blue-france-main-525);
    }
  }
</style>
