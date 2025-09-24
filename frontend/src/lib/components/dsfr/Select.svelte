<script
  lang="ts"
  generics="Value extends number | string, Option extends { value: Value, label: string }"
>
  import type { ClassValue, HTMLSelectAttributes } from 'svelte/elements'

  type SelectProps = {
    id: string
    selected: Value
    label: string
    options: Option[]
    hideLabel?: boolean
    groupClass?: ClassValue
  } & HTMLSelectAttributes

  let {
    id,
    selected = $bindable(),
    label,
    options,
    hideLabel = false,
    groupClass,
    ...props
  }: SelectProps = $props()
</script>

<div class={["fr-select-group", groupClass]}>
  <label class={['fr-label', { 'fr-sr-only': hideLabel }]} for={id}>
    {label}
  </label>

  <select {...props} {id} bind:value={selected} class={["fr-select", props.class]}>
    {#each options as option}
      <option value={option.value}>{option.label}</option>
    {/each}
  </select>
</div>
