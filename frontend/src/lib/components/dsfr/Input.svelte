<script lang="ts">
  import type { ClassValue, HTMLInputAttributes } from 'svelte/elements'

  let {
    id,
    value = $bindable(),
    label,
    help,
    error,
    variant = 'normal',
    groupClass,
    ...props
  }: {
    id: string
    value: string
    label: string
    help?: string
    error?: string
    variant?: 'light' | 'normal'
    groupClass?: ClassValue
  } & HTMLInputAttributes = $props()

  const describedBy = $derived(error ? `input-${id}-messages` : help ? `${id}-help` : undefined)
</script>

<div class={['fr-input-group', { 'fr-input-group--error': !!error }, groupClass]}>
  <label class="fr-label" for={id}>
    {label}
    {#if help}
      <span id="{id}-help" class="fr-hint-text">{help}</span>
    {/if}
  </label>
  <input
    {...props}
    bind:value
    {id}
    aria-describedby={describedBy}
    aria-invalid={error ? 'true' : undefined}
    class={['fr-input', { 'bg-white!': variant === 'light' }, props.class]}
  />
  {#if error}
    <div class="fr-messages-group" id="input-{id}-messages" aria-live="polite">
      <p class="fr-message fr-message--error">{error}</p>
    </div>
  {/if}
</div>

<style lang="postcss">
  :root[data-fr-theme='light'] {
    .fr-input {
      --border-action-high-blue-france: var(--blue-france-main-525);
    }
  }
  @media (prefers-color-scheme: light) {
    :root[data-fr-theme='system'] {
      .fr-input {
        --border-action-high-blue-france: var(--blue-france-main-525);
      }
    }
  }
</style>
