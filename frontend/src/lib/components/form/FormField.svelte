<script module lang="ts">
  import type { BaseFormFieldProps } from '$lib/utils/form'
  import type { Snippet } from 'svelte'

  export type FormFieldProps = {
    formItem: Snippet<[{ 'aria-describedby': string; id: string }]>
  } & Omit<BaseFormFieldProps<'input' | 'select' | 'checkbox'>, 'value'>
</script>

<script lang="ts">
  let { id, label, component, help, errors, formItem }: FormFieldProps = $props()

  const messagesId = $derived(`${id}-messages`)
  const props_ = $derived({ 'aria-describedby': messagesId, id })
  const error = $derived(errors?.[id])
</script>

<div class={[`fr-${component}-group`, { [`fr-${component}-group--error`]: !!error }]}>
  {#if component === 'checkbox'}
    {@render formItem?.(props_)}
  {/if}

  <label class="fr-label" for={id}>
    {label}
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
