<script module lang="ts">
  export type FormCheckboxGroupProps = {
    options: Option<string>[]
    // The admin form only holds the keys the user touched, so the group may
    // render before its own key exists.
    value?: string[]
  } & Omit<BaseFormFieldProps<'checkbox-group', string[]>, 'value'>
</script>

<script lang="ts">
  import type { BaseFormFieldProps, Option } from '$lib/utils/form'
  import { FormField, FormFieldset } from '.'

  let { value = $bindable(), disabled, options, ...props }: FormCheckboxGroupProps = $props()

  function onToggle(option: string, checked: boolean) {
    value = checked ? [...(value ?? []), option] : (value ?? []).filter((v) => v !== option)
  }
</script>

<FormFieldset {...props} component="fieldset">
  {#snippet formItem({ id })}
    {#each options as opt (opt.value)}
      <div class="fr-fieldset__element">
        <FormField id={`${id}-${opt.value}`} label={opt.label} component="checkbox">
          {#snippet formItem({ id })}
            <input
              name={id}
              {id}
              type="checkbox"
              value={opt.value}
              {disabled}
              checked={value?.includes(opt.value) ?? false}
              onchange={(e) => onToggle(opt.value, e.currentTarget.checked)}
            />
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
