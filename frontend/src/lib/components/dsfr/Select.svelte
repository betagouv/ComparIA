<script
  lang="ts"
  generics="Value extends number | string, Option extends { value: Value, label: string }"
>
  import type { ClassValue, HTMLSelectAttributes } from 'svelte/elements'

  type SelectProps = {
    id: string
    selected: Value
    label: string
    help?: string
    options: Option[]
    hideLabel?: boolean
    reserveHintSpace?: boolean
    groupClass?: ClassValue
  } & HTMLSelectAttributes

  let {
    id,
    selected = $bindable(),
    label,
    help,
    options,
    hideLabel = false,
    reserveHintSpace = false,
    groupClass,
    ...props
  }: SelectProps = $props()
</script>

<div class={['fr-select-group', groupClass]}>
  <label class={['fr-label', { 'fr-sr-only': hideLabel }]} for={id}>
    {label}
    {#if help}
      <span id={`${id}-help`} class="fr-hint-text">{help}</span>
    {:else if reserveHintSpace}
      <span class="fr-hint-text" aria-hidden="true">&nbsp;</span>
    {/if}
  </label>

  <select
    {...props}
    {id}
    bind:value={selected}
    aria-describedby={help ? `${id}-help` : props['aria-describedby']}
    class={['fr-select', props.class]}
  >
    {#each options as option (option.value)}
      <option value={option.value}>{option.label}</option>
    {/each}
  </select>
</div>

<style lang="postcss">
  .fr-select {
    --border-plain-grey: var(--blue-france-main-525);
    --background-contrast-grey: var(--blue-ecume-975-75);
  }
</style>
