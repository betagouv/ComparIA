<script module lang="ts">
  export type FormCheckboxProps = BaseFormFieldProps<'checkbox', boolean>
</script>

<script lang="ts">
  import type { BaseFormFieldProps } from '$lib/utils/form'
  import { FormField } from '.'

  let { value = $bindable(), disabled, ...props }: FormCheckboxProps = $props()
</script>

<FormField {...props} component="checkbox">
  {#snippet formItem({ ...fieldProps })}
    <input {...fieldProps} {disabled} type="checkbox" bind:checked={value} />
  {/snippet}
</FormField>

<style lang="postcss">
  input[type='checkbox'] {
    :global(& + label) {
      --border-action-high-blue-france: var(--blue-france-main-525);
      --border-active-blue-france: var(--blue-france-main-525);
      --background-active-blue-france: var(--blue-france-main-525);
    }
  }
</style>
