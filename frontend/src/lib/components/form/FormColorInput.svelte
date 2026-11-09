<script module lang="ts">
  export type FormColorInputProps = BaseFormFieldProps<'input'>
</script>

<script lang="ts">
  import { isHexColor } from '$lib/theme'
  import type { BaseFormFieldProps } from '$lib/utils/form'
  import { FormField } from '.'

  let {
    value = $bindable(),
    disabled,
    ...props
  }: Omit<FormColorInputProps, 'component'> & { value: string } = $props()

  function updateColor(nextValue: string) {
    value = nextValue.toUpperCase()
  }
</script>

<FormField {...props} component="input">
  {#snippet formItem(fieldProps)}
    <div class="gap-3 mt-2 sm:flex-row sm:items-center flex flex-col">
      <input
        id="{fieldProps.id}-picker"
        type="color"
        value={isHexColor(value) ? value : '#000000'}
        aria-label={props.label}
        aria-describedby={fieldProps['aria-describedby']}
        {disabled}
        oninput={(event) => updateColor(event.currentTarget.value)}
        class="h-10 w-14 rounded p-1 cursor-pointer border border-[--border-default-grey] disabled:cursor-not-allowed"
      />
      <input
        {...fieldProps}
        type="text"
        bind:value
        oninput={(event) => updateColor(event.currentTarget.value)}
        autocomplete="off"
        spellcheck="false"
        placeholder="#6464F3"
        {disabled}
        class="fr-input max-w-[12rem]"
      />
    </div>
  {/snippet}
</FormField>
