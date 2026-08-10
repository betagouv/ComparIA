<script lang="ts">
  import type { Snippet } from 'svelte'
  import type { ClassValue, HTMLInputAttributes } from 'svelte/elements'

  let {
    id,
    value = $bindable(),
    label,
    help,
    error,
    variant = 'normal',
    groupClass,
    tooltip,
    ...props
  }: {
    id: string
    value: string
    label: string
    help?: string
    error?: string
    variant?: 'light' | 'normal'
    groupClass?: ClassValue
    /** Sits beside the label text. Use for a hint too long to leave on screen. */
    tooltip?: Snippet
  } & HTMLInputAttributes = $props()
</script>

{#snippet labelEl()}
  <label class="fr-label" for={id}>
    {label}
    {#if help}
      <span class="fr-hint-text">{help}</span>
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
  <input
    {...props}
    bind:value
    {id}
    aria-describedby="input-{id}-messages"
    class={['fr-input', { 'bg-white!': variant === 'light' }, props.class]}
  />
  {#if error}
    <div class="fr-messages-group" id="input-{id}-messages" aria-live="polite">
      <p class="fr-message fr-message--error">{error}</p>
    </div>
  {/if}
</div>

<style lang="postcss">
  .fr-input {
    --border-action-high-blue-france: var(--blue-france-main-525);
  }
</style>
