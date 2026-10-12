<script
  lang="ts"
  generics="Value extends string, Option extends { value: Value, label: string, icon?: string }"
>
  import type { ClassValue, HTMLFieldsetAttributes } from 'svelte/elements'
  import Icon from './Icon.svelte'

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
          {#if option.icon}
            {#if option.icon.length < 3}
              <!-- Decorative: the label already says which view this is. -->
              <span aria-hidden="true" class="me-2">{option.icon}</span>
            {:else}
              <Icon size="xs" icon={option.icon} block class="me-2" />
            {/if}
          {/if}
          {option.label ?? option.value}
        </label>
      </div>
    {/each}
  </div>
</fieldset>

<style lang="postcss">
  label {
    --border-active-blue-france: var(--blue-france-main-525);
    --text-active-blue-france: var(--blue-france-main-525);
  }
</style>
