<script module lang="ts">
  export type FormRadioGroupProps = {
    options: Option<string>[]
    // The admin form only holds the keys the user touched, so the group may
    // render before its own key exists.
  } & BaseFormFieldProps<'radio'>
</script>

<script lang="ts">
  import type { BaseFormFieldProps, Option } from '$lib/utils/form'
  import { FormField, FormFieldset } from '.'

  let {
    value = $bindable(),
    disabled,
    options,
    ...props
  }: Omit<FormRadioGroupProps, 'component'> & { value?: string } = $props()
</script>

<FormFieldset {...props} component="fieldset">
  {#snippet formItem({ id })}
    {#each options as opt (opt.value)}
      <div class="fr-fieldset__element fr-fieldset__element--inline">
        <FormField id={`${id}-${opt.value}`} label={opt.label} component="radio">
          {#snippet formItem({ id })}
            <input name={id} {id} type="radio" bind:group={value} value={opt.value} {disabled} />
          {/snippet}
        </FormField>
      </div>
    {/each}
  {/snippet}
</FormFieldset>

<style lang="postcss">
  .fr-fieldset__element {
    :global(input[type='radio'] + label) {
      --border-action-high-blue-france: var(--blue-france-main-525);
      --border-active-blue-france: var(--blue-france-main-525);
      --background-active-blue-france: var(--blue-france-main-525);
    }
  }
</style>
