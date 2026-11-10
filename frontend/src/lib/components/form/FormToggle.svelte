<script module lang="ts">
  export type FormToggleProps = {
    checkKind?: 'truth' | 'active' | 'none'
    labelSnippet?: Snippet<[label: string]>
  } & BaseFormFieldProps<'toggle'>
</script>

<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { BaseFormFieldProps } from '$lib/utils/form'
  import type { Snippet } from 'svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    value = $bindable(),
    id,
    label,
    help,
    disabled,
    hidden,
    errors,
    checkKind = 'truth',
    labelSnippet,
    ...props
  }: Omit<FormToggleProps, 'component'> & { value: boolean } & SvelteHTMLElements['div'] = $props()

  const messagesId = $derived(`${id}-messages`)
  const hintId = $derived(`${id}-hint`)
  const checkedLabel = $derived(
    checkKind === 'none' ? '' : m[`words.${checkKind === 'truth' ? 'yes' : 'activated'}`]()
  )
  const uncheckedLabel = $derived(
    checkKind === 'none' ? '' : m[`words.${checkKind === 'truth' ? 'no' : 'deactivated'}`]()
  )
  const error = $derived(errors?.[id])
</script>

<div
  {...props}
  class={['fr-toggle', { 'fr-toggle--error': !!error, 'hidden!': hidden }, props.class ?? 'mb-6!']}
>
  <input
    {id}
    type="checkbox"
    bind:checked={value}
    {disabled}
    class="fr-toggle__input"
    aria-describedby="{hintId} {messagesId}"
    aria-invalid={error ? 'true' : undefined}
  />

  <label
    class="fr-toggle__label w-full!"
    for={id}
    data-fr-checked-label={checkedLabel}
    data-fr-unchecked-label={uncheckedLabel}
  >
    {#if labelSnippet}
      {@render labelSnippet(label)}
    {:else}
      {label}
    {/if}
  </label>

  {#if help}
    <span id={hintId} class="fr-hint-text">{help}</span>
  {/if}

  <div class="fr-messages-group" id={messagesId} aria-live="polite">
    {#if error}
      <p class="fr-message fr-message--error">{error}</p>
    {/if}
  </div>
</div>

<style lang="postcss">
  .fr-toggle {
    --border-action-high-blue-france: var(--blue-france-main-525);
    --text-active-blue-france: var(--blue-france-main-525);

    input[type='checkbox']:checked ~ .fr-toggle__label::after {
      --data-uri-svg: var(--brand-toggle-check);
    }
    label::before {
      --data-uri-svg: var(--brand-toggle-track);
    }
    input[type='checkbox']:checked ~ .fr-toggle__label::before {
      --data-uri-svg: var(--brand-toggle-track-checked);
    }
  }
</style>
