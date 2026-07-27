<script lang="ts">
  import Selector from '$components/Selector.svelte'
  import { Icon } from '$components/dsfr'

  type IconOption = {
    value: string
    label: string
  }

  let {
    id,
    label,
    options,
    value = $bindable(),
    onchange
  }: {
    id: string
    label: string
    options: IconOption[]
    value: string
    onchange?: (value: string) => void
  } = $props()
</script>

<fieldset class="fr-fieldset mb-4!">
  <legend class="fr-fieldset__legend fr-text--regular">{label}</legend>
  <Selector
    {id}
    kind="radio"
    choices={options}
    bind:value
    onChange={onchange}
    containerClass="grid grid-cols-4 gap-2 sm:grid-cols-8"
    choiceClass="fr-btn fr-btn--tertiary min-h-12 cursor-pointer justify-center rounded-lg p-2!"
  >
    {#snippet option(option, labelProps, input)}
      <label {...labelProps} title={option.label}>
        {@render input(option, { required: true, 'aria-label': option.label })}
        <Icon icon={option.value} aria-hidden="true" />
        <span class="sr-only">{option.label}</span>
      </label>
    {/snippet}
  </Selector>
</fieldset>
