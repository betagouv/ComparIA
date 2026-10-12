<script module lang="ts">
  import type { BaseFormFieldProps, FormItemSnippetProps } from '$lib/utils/form'
  import type { Snippet } from 'svelte'

  export type FormFieldProps = {
    formItem: Snippet<[FormItemSnippetProps]>
  } & BaseFormFieldProps<'input' | 'select' | 'checkbox' | 'radio'>
</script>

<script lang="ts">
  let { id, label, required, hidden, component, help, errors, formItem }: FormFieldProps = $props()

  const messagesId = $derived(`${id}-messages`)
  const error = $derived(errors?.[id])
  const props_ = $derived({
    'aria-describedby': messagesId,
    'aria-invalid': error ? ('true' as const) : undefined,
    id,
    required
  })
  const formItemFirst = $derived(['radio', 'checkbox'].includes(component))
</script>

<div
  class={[
    `fr-${component}-group`,
    {
      [`fr-${component}-group--error`]: !!error,
      hidden,
      [`fr-${component}-group--sm`]: formItemFirst
    }
  ]}
>
  {#if formItemFirst}
    {@render formItem?.(props_)}
  {/if}

  <label class="fr-label" for={id}>
    <span class={{ 'font-bold': !formItemFirst }}>{label}</span>
    {#if required}<span class="text-error">*</span>{/if}
    {#if help}
      <span class="fr-hint-text">{help}</span>
    {/if}
  </label>

  {#if !formItemFirst}
    {@render formItem?.(props_)}
  {/if}

  <div class="fr-messages-group" id={messagesId} aria-live="polite">
    {#if error}
      <p class="fr-message fr-message--error">{error}</p>
    {/if}
  </div>
</div>

<style lang="postcss">
</style>
