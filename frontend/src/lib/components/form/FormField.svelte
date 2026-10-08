<script module lang="ts">
  import type { BaseFormFieldProps, FormItemSnippetProps } from '$lib/utils/form'
  import type { Snippet } from 'svelte'

  export type FormFieldProps = {
    formItem: Snippet<[FormItemSnippetProps]>
  } & BaseFormFieldProps<'input' | 'select' | 'checkbox'>
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
</script>

<div class={[`fr-${component}-group`, { [`fr-${component}-group--error`]: !!error, hidden }]}>
  {#if component === 'checkbox'}
    {@render formItem?.(props_)}
  {/if}

  <label class="fr-label" for={id}>
    {label}
    {#if required}<span class="text-error">*</span>{/if}
    {#if help}
      <span class="fr-hint-text">{help}</span>
    {/if}
  </label>

  {#if component !== 'checkbox'}
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
