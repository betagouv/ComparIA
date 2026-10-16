<script lang="ts">
  import type { ClassValue, HTMLInputAttributes } from 'svelte/elements'

  let {
    id,
    value = $bindable(),
    label,
    help,
    hint,
    error,
    variant = 'normal',
    groupClass,
    ...props
  }: {
    id: string
    value: string
    label: string
    help?: string
    /** Under the field, such as the typed value spelled out. */
    hint?: string
    error?: string
    variant?: 'light' | 'normal'
    groupClass?: ClassValue
  } & HTMLInputAttributes = $props()
</script>

<div class={['fr-input-group', { 'fr-input-group--error': !!error }, groupClass]}>
  <label class="fr-label" for={id}>
    {label}
    {#if help}
      <span class="fr-hint-text">{help}</span>
    {/if}
  </label>
  <input
    {...props}
    bind:value
    {id}
    aria-invalid={error ? 'true' : undefined}
    aria-describedby={hint ? `input-${id}-hint input-${id}-messages` : `input-${id}-messages`}
    class={['fr-input', { 'bg-white!': variant === 'light' }, props.class]}
  />
  {#if hint}
    <p id="input-{id}-hint" class="fr-hint-text mt-2! mb-0!">{hint}</p>
  {/if}
  <!-- Always rendered: a live region has to exist before the message lands in
       it, otherwise screen readers announce nothing. -->
  <div class="fr-messages-group" id="input-{id}-messages" aria-live="polite">
    {#if error}
      <p class="fr-message fr-message--error">{error}</p>
    {/if}
  </div>
</div>

<style lang="postcss">
  .fr-input {
    --border-action-high-blue-france: var(--blue-france-main-525);
  }
</style>
