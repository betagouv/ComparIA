<script lang="ts">
  import { Button } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import type { HTMLInputAttributes } from 'svelte/elements'

  let {
    id,
    value = $bindable(),
    label,
    placeholder = label,
    class: classes,
    ...props
  }: {
    id: string
    value: string
    label: string
  } & HTMLInputAttributes = $props()
</script>

<div class={['fr-search-bar', classes]} role="search">
  <label class="fr-label" for={id}>{label}</label>
  <input
    bind:value
    {...props}
    class="fr-input placeholder:overflow-visible"
    {placeholder}
    {id}
    type="search"
  />
  <Button text={m['words.search']()} title={m['words.search']()} iconOnly />
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
