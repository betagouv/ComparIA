<script module lang="ts">
  export type FormInputProps = {
    type: HTMLInputElement['type']
    step?: HTMLInputElement['step']
  } & BaseFormFieldProps<'input', string | number>
</script>

<script lang="ts">
  import type { BaseFormFieldProps } from '$lib/utils/form'
  import { FormField } from '.'

  let { value = $bindable(), type, step, ...props }: FormInputProps = $props()
</script>

<FormField {...props} component="input">
  {#snippet formItem(fieldProps)}
    <input {...fieldProps} {type} {step} bind:value class="fr-input" />
  {/snippet}
</FormField>

<style lang="postcss">
  .fr-input {
    --border-plain-grey: var(--blue-france-main-525);
    --background-contrast-grey: var(--blue-ecume-975-75);
  }
</style>
