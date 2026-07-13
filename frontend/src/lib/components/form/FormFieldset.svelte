<script module lang="ts">
  import type { BaseFormFieldProps } from '$lib/utils/form'
  import type { Snippet } from 'svelte'

  export type FormFieldsetProps = {
    formItem: Snippet<[{ 'aria-describedby': string; id: string }]>
  } & Omit<BaseFormFieldProps<'fieldset'>, 'value'>
</script>

<script lang="ts">
  let { id, label, help, component: _component, errors, formItem }: FormFieldsetProps = $props()

  const legendId = $derived(`${id}-legend`)
  const messagesId = $derived(`${id}-messages`)
  const error = $derived(errors?.[id])
</script>

<fieldset
  id="fieldset-{id}"
  aria-labelledby={`${legendId} ${messagesId}`}
  class={['fr-fieldset cg-border! p-4!', { 'fr-fieldset--error': !!error }]}
>
  <legend
    class="fr-fieldset__legend--regular fr-fieldset__legend pb-0! px-2! w-auto!"
    id={legendId}
  >
    {label}
    {#if help}
      <span class="fr-hint-text">{help}</span>
    {/if}
  </legend>

  {@render formItem?.({ 'aria-describedby': '', id })}

  {#if error}
    <div class="fr-messages-group" id={messagesId} aria-live="polite">
      <p class="fr-message fr-message--error">{error}</p>
    </div>
  {/if}
</fieldset>

<style lang="postcss">
</style>
