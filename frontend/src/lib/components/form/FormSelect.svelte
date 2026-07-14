<script module lang="ts">
  export type FormSelectProps = {
    options: Option<string | null>[]
  } & BaseFormFieldProps<'select', string | null>
</script>

<script lang="ts">
  import type { BaseFormFieldProps, Option } from '$lib/utils/form'
  import { FormField } from '.'

  let { value = $bindable(), options, ...props }: FormSelectProps = $props()
</script>

<FormField {...props} component="select">
  {#snippet formItem(fieldProps)}
    <select {...fieldProps} bind:value class="fr-select">
      {#each options as option (option.value)}
        <option value={option.value}>{option.label}</option>
      {/each}
    </select>
  {/snippet}
</FormField>

<style lang="postcss">
  .fr-select {
    --border-plain-grey: var(--blue-france-main-525);
    --background-contrast-grey: var(--blue-ecume-975-75);
  }
</style>
