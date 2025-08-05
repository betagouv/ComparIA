<script lang="ts" generics="T extends {id: string; label: string; content?: string}">
  import type { Snippet } from 'svelte'

  let {
    tabs,
    label,
    tab
  }: {
    tabs: T[]
    label: string
    tab?: Snippet<[T]>
  } = $props()
</script>

<div class="fr-tabs">
  <ul class="fr-tabs__list" role="tablist" aria-label={label}>
    {#each tabs as item, i}
      <li role="presentation">
        <button
          type="button"
          id={`tab-${item.id}`}
          class="fr-tabs__tab"
          tabindex={i === 0 ? 0 : -1}
          role="tab"
          aria-selected="true"
          aria-controls={`tab-${item.id}-panel`}
        >
          {item.label}
        </button>
      </li>
    {/each}
  </ul>
  {#each tabs as item, i}
    <div
      id={`tab-${item.id}-panel`}
      role="tabpanel"
      aria-labelledby={`tab-${item.id}`}
      tabindex="0"
      class={['fr-tabs__panel', i === 0 ? 'fr-tabs__panel--selected' : '']}
    >
      {#if item.content}{item.content}{:else}{@render tab?.(item)}{/if}
    </div>
  {/each}
</div>
