<script lang="ts">
  import type { ClassValue, HTMLTextareaAttributes } from 'svelte/elements'

  let {
    id,
    value = $bindable(),
    label,
    help,
    error,
    groupClass,
    ...props
  }: {
    id: string
    value: string
    label: string
    help?: string
    error?: string
    groupClass?: ClassValue
  } & HTMLTextareaAttributes = $props()
</script>

<div class={['fr-input-group', { 'fr-input-group--error': !!error }, groupClass]}>
  <label class="fr-label" for={id}>
    {label}
    {#if help}
      <span class="fr-hint-text">{help}</span>
    {/if}
  </label>
  <textarea
    {...props}
    bind:value
    {id}
    aria-describedby="input-{id}-messages"
    class={['fr-input', props.class]}
  ></textarea>
  {#if error}
    <div class="fr-messages-group" id="input-{id}-messages" aria-live="polite">
      <p class="fr-message fr-message--error">{error}</p>
    </div>
  {/if}
</div>
