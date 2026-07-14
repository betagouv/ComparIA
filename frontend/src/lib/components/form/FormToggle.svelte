<script module lang="ts">
  export type FormToggleProps = {
    checkKind?: 'truth' | 'active'
  } & BaseFormFieldProps<'toggle', boolean>
</script>

<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { BaseFormFieldProps } from '$lib/utils/form'

  let {
    value = $bindable(),
    id,
    disabled,
    label,
    help,
    errors,
    checkKind = 'truth'
  }: FormToggleProps = $props()

  const messagesId = $derived(`${id}-messages`)
  const hintId = $derived(`${id}-hint`)
  const checkedLabel = $derived(m[`words.${checkKind === 'truth' ? 'yes' : 'activated'}`]())
  const uncheckedLabel = $derived(m[`words.${checkKind === 'truth' ? 'no' : 'deactivated'}`]())
  const error = $derived(errors?.[id])
</script>

<div class={['fr-toggle mb-6!', { 'fr-toggle--error': !!error }]}>
  <input
    {id}
    type="checkbox"
    bind:checked={value}
    {disabled}
    class="fr-toggle__input"
    aria-describedby="{hintId} {messagesId}"
  />

  <label
    class="fr-toggle__label"
    for={id}
    data-fr-checked-label={checkedLabel}
    data-fr-unchecked-label={uncheckedLabel}
  >
    {label}
  </label>

  {#if help}
    <span id={hintId} class="fr-hint-text">{help}</span>
  {/if}

  {#if error}
    <div class="fr-messages-group" id={messagesId} aria-live="polite">
      <p class="fr-message fr-message--error">{error}</p>
    </div>
  {/if}
</div>

<style lang="postcss">
  input[type='checkbox'] {
    --border-action-high-blue-france: var(--blue-france-main-525);
    --text-active-blue-france: var(--blue-france-main-525);
  }
</style>
