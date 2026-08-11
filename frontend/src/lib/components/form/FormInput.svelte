<script module lang="ts">
  export type FormInputProps = {
    type: HTMLInputElement['type']
    placeholder: HTMLInputElement['placeholder']
    step?: HTMLInputElement['step']
  } & BaseFormFieldProps<'input', string | number>
</script>

<script lang="ts">
  import type { BaseFormFieldProps } from '$lib/utils/form'
  import type { SvelteHTMLElements } from 'svelte/elements'
  import { FormField } from '.'

  let {
    value = $bindable(),
    type,
    disabled,
    placeholder,
    step,
    children,
    ...props
  }: FormInputProps & SvelteHTMLElements['div'] = $props()
</script>

<FormField {...props} component="input">
  {#snippet formItem(fieldProps)}
    <div class="gap-3 mt-2 flex">
      <input {...fieldProps} {type} {placeholder} {disabled} {step} bind:value class="fr-input" />
      {@render children?.()}
    </div>
  {/snippet}
</FormField>

<style lang="postcss">
  .fr-input {
    --border-plain-grey: var(--blue-france-main-525);
    --background-contrast-grey: var(--blue-ecume-975-75);
  }
</style>
