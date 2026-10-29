<script module lang="ts">
  export type FormTextareaProps = {
    placeholder?: HTMLTextAreaElement['placeholder']
    rows?: number
  } & BaseFormFieldProps<'textarea'>
</script>

<script lang="ts">
  import type { BaseFormFieldProps } from '$lib/utils/form'
  import { FormField } from '.'

  let {
    value = $bindable(),
    disabled,
    placeholder,
    rows = 4,
    ...props
  }: FormTextareaProps & { value: string } = $props()
</script>

<!-- DSFR styles a textarea as an input group. -->
<FormField {...props} component="input">
  {#snippet formItem(fieldProps)}
    <textarea {...fieldProps} {placeholder} {disabled} {rows} bind:value class="fr-input mt-2"
    ></textarea>
  {/snippet}
</FormField>

<style lang="postcss">
  .fr-input {
    --border-plain-grey: var(--blue-france-main-525);
    --background-contrast-grey: var(--blue-ecume-975-75);
  }
</style>
