<script lang="ts">
  import type { HTMLInputAttributes } from 'svelte/elements'

  let {
    id,
    label,
    hint,
    error,
    value = $bindable(),
    disabled = false,
    ...props
  }: {
    id: string
    label: string
    hint: string
    error?: string
    value: string
    disabled?: boolean
  } & Omit<HTMLInputAttributes, 'type' | 'value' | 'disabled'> = $props()

  const isValidHex = (color: string) => /^#[0-9A-Fa-f]{6}$/.test(color)

  function updateColor(nextValue: string) {
    value = nextValue.toUpperCase()
  }
</script>

<div class={['fr-input-group', { 'fr-input-group--error': !!error }]}>
  <label class="fr-label" for={`${id}-text`}>
    {label}
    <span class="fr-hint-text">{hint}</span>
  </label>
  <div class="gap-3 sm:flex-row sm:items-center flex flex-col">
    <input
      {...props}
      id={`${id}-picker`}
      type="color"
      value={isValidHex(value) ? value : '#000000'}
      aria-label={label}
      aria-describedby={`${id}-messages`}
      {disabled}
      oninput={(event) => updateColor(event.currentTarget.value)}
      class="h-10 w-14 rounded p-1 cursor-pointer border border-[--border-default-grey] disabled:cursor-not-allowed"
    />
    <input
      id={`${id}-text`}
      type="text"
      bind:value
      oninput={(event) => updateColor(event.currentTarget.value)}
      aria-describedby={`${id}-messages`}
      aria-invalid={error ? 'true' : undefined}
      autocomplete="off"
      spellcheck="false"
      placeholder="#6464F3"
      {disabled}
      class="fr-input max-w-[12rem]"
    />
  </div>
  <div class="fr-messages-group" id={`${id}-messages`} aria-live="polite">
    {#if error}
      <p class="fr-message fr-message--error">{error}</p>
    {/if}
  </div>
</div>
