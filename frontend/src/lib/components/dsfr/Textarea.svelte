<script lang="ts">
  import type { Snippet } from 'svelte'
  import type { ClassValue, HTMLTextareaAttributes } from 'svelte/elements'

  let {
    id,
    value = $bindable(),
    label,
    help,
    error,
    groupClass,
    tooltip,
    ...props
  }: {
    id: string
    value: string
    label: string
    help?: string
    error?: string
    groupClass?: ClassValue
    /** Sits beside the label text. Use for a hint too long to leave on screen. */
    tooltip?: Snippet
  } & HTMLTextareaAttributes = $props()

  const describedBy = $derived(
    [help ? `${id}-help` : '', error ? `${id}-messages` : ''].filter(Boolean).join(' ') || undefined
  )
</script>

{#snippet labelEl()}
  <label class="fr-label" for={id}>
    {label}
    {#if help}
      <span id={`${id}-help`} class="fr-hint-text">{help}</span>
    {/if}
  </label>
{/snippet}

<div class={['fr-input-group', { 'fr-input-group--error': !!error }, groupClass]}>
  {#if tooltip}
    <div class="gap-2 flex items-center">
      {@render labelEl()}
      {@render tooltip()}
    </div>
  {:else}
    {@render labelEl()}
  {/if}
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
