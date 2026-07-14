<script module lang="ts">
  export type FormCheckboxGroupProps = {
    options: Option<string>[]
  } & BaseFormFieldProps<'checkbox-group', string[]>
</script>

<script lang="ts">
  import type { BaseFormFieldProps, Option } from '$lib/utils/form'
  import { FormField, FormFieldset } from '.'

  let { value = $bindable(), disabled, options, ...props }: FormCheckboxGroupProps = $props()
</script>

<FormFieldset {...props} component="fieldset">
  {#snippet formItem({ id })}
    {#each options as opt (opt.value)}
      <div class="fr-fieldset__element">
        <FormField id={`${id}-${opt.value}`} label={opt.label} component="checkbox">
          {#snippet formItem({ id })}
            <input name={id} {id} type="checkbox" value={opt.value} {disabled} bind:group={value} />
          {/snippet}
        </FormField>
      </div>
    {/each}
  {/snippet}
</FormFieldset>

<style lang="postcss">
  .fr-fieldset__element {
    :global(input[type='checkbox'] + label) {
      --border-action-high-blue-france: var(--blue-france-main-525);
      --border-active-blue-france: var(--blue-france-main-525);
      --background-active-blue-france: var(--blue-france-main-525);
    }
  }
</style>
