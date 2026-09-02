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

  const describedBy = $derived(
    [help ? `${id}-help` : '', error ? `${id}-messages` : ''].filter(Boolean).join(' ') || undefined
  )
</script>

<div class={['fr-input-group', { 'fr-input-group--error': !!error }, groupClass]}>
  <label class="fr-label" for={id}>
    {label}
    {#if help}
      <span id={`${id}-help`} class="fr-hint-text">{help}</span>
    {/if}
  </label>
  <textarea
    {...props}
    bind:value
    {id}
    aria-describedby={describedBy}
    aria-invalid={error ? 'true' : undefined}
    class={['fr-input', props.class]}
  ></textarea>
  {#if error}
    <div class="fr-messages-group" id={`${id}-messages`} aria-live="polite">
      <p class="fr-message fr-message--error">{error}</p>
    </div>
  {/if}
</div>
