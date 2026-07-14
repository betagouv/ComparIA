<script module lang="ts">
  import type { BaseFormFieldProps } from '$lib/utils/form'
  import type { Snippet } from 'svelte'

  export type FormFieldProps = {
    formItem: Snippet<[{ 'aria-describedby': string; id: string; required?: boolean }]>
  } & Omit<BaseFormFieldProps<'input' | 'select' | 'checkbox', string | boolean | null>, 'value'>
</script>

<script lang="ts">
  let { id, label, required, component, help, errors, formItem }: FormFieldProps = $props()

  const messagesId = $derived(`${id}-messages`)
  const props_ = $derived({ 'aria-describedby': messagesId, id, required })
  const error = $derived(errors?.[id])
</script>

<div class={[`fr-${component}-group`, { [`fr-${component}-group--error`]: !!error }]}>
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

  {#if error}
    <div class="fr-messages-group" id={messagesId} aria-live="polite">
      <p class="fr-message fr-message--error">{error}</p>
    </div>
  {/if}
</div>

<style lang="postcss">
</style>
