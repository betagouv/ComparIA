<script lang="ts">
  import { sanitize } from '$lib/utils/commons'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    id,
    checked = $bindable(),
    label,
    help,
    error,
    ...props
  }: {
    id: string
    checked: boolean
    label: string
    help?: string
    error?: string
  } & SvelteHTMLElements['label'] = $props()
</script>

<div class="fr-checkbox-group fr-checkbox-group--sm" class:fr-checkbox-group--error={!!error}>
  <input {id} aria-describedby="{id}-error-messages" type="checkbox" bind:checked />
  <label {...props} class={['fr-label fr-text--sm block!', props.class]} for={id}>
    {@html sanitize(label)}
    {#if help}
      <p class="fr-message">{help}</p>
    {/if}
  </label>
  <div
    class={['fr-messages-group', { hidden: !error }]}
    id="{id}-error-messages"
    aria-live="assertive"
  >
    <p class="fr-message fr-message--error" id="checkbox-error-message-error">
      {error}
    </p>
  </div>
</div>

<style lang="postcss">
  .fr-checkbox-group input[type='checkbox'] + label:before {
    --border-action-high-blue-france: var(--blue-france-main-525);
  }

  .fr-checkbox-group input[type='checkbox']:checked + label:before {
    --border-active-blue-france: var(--blue-france-main-525);
    background-color: var(--blue-france-main-525);
  }
</style>
