<script
  lang="ts"
  generics="Value extends number | string, Option extends { value: Value, label: string }"
>
  import type { HTMLSelectAttributes } from 'svelte/elements'

  type SelectProps = {
    id: string
    selected: Value
    label: string
    options: Option[]
    hideLabel?: boolean
  } & HTMLSelectAttributes

  let {
    id,
    selected = $bindable(),
    label,
    options,
    hideLabel = false,
    ...props
  }: SelectProps = $props()
</script>

<div class="fr-select-group">
  <label class={['fr-label', { 'fr-sr-only': hideLabel }]} for={id}>
    {label}
  </label>

  <select {...props} bind:value={selected} class="fr-select" {id} name="table-footer-select-7847">
    {#each options as option}
      <option value={option.value}>{option.label}</option>
    {/each}
  </select>
</div>
