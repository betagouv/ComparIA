<script module lang="ts">
  export type FormInputProps = {
    type: HTMLInputElement['type']
    placeholder?: HTMLInputElement['placeholder']
    step?: HTMLInputElement['step']
    maxlength?: HTMLInputElement['maxLength']
    // Id of a <datalist> suggesting values without limiting the field to them.
    list?: string
  } & BaseFormFieldProps<'input'>
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
    maxlength,
    list,
    children,
    ...props
  }: FormInputProps & { value: string | number } & SvelteHTMLElements['div'] = $props()
</script>

<FormField {...props} component="input">
  {#snippet formItem(fieldProps)}
    <div class="gap-3 mt-2 flex">
      <input
        {...fieldProps}
        {type}
        {placeholder}
        {disabled}
        {step}
        {maxlength}
        {list}
        bind:value
        class="fr-input"
      />
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
