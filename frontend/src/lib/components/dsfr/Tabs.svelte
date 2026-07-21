<script
  lang="ts"
  generics="T extends { id: string; label: string; href?: string; content?: string, icon?: string }"
>
  import type { Snippet } from 'svelte'
  import type { ClassValue, SvelteHTMLElements } from 'svelte/elements'
  import { Icon } from '.'

  let {
    tabs,
    label,
    initialId = tabs[0].id,
    noBorders = false,
    panelClass = '',
    kind = 'tab',
    tab,
    ...props
  }: {
    tabs: Readonly<T[]>
    label: string
    initialId?: T['id']
    noBorders?: boolean
    panelClass?: ClassValue
    kind?: 'tab' | 'nav'
    tab?: Snippet<[T]>
  } & SvelteHTMLElements['div'] = $props()

  const getInitialId = () => initialId
  let currentTabId = $state(getInitialId())

  function selectTab(index: number) {
    const tab = tabs[index]
    if (!tab) return
    currentTabId = tab.id
    queueMicrotask(() => document.getElementById(`tab-${tab.id}`)?.focus())
  }

  function handleKeydown(event: KeyboardEvent, index: number) {
    let nextIndex: number | undefined
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % tabs.length
    if (event.key === 'ArrowLeft') nextIndex = (index - 1 + tabs.length) % tabs.length
    if (event.key === 'Home') nextIndex = 0
    if (event.key === 'End') nextIndex = tabs.length - 1
    if (nextIndex === undefined) return

    event.preventDefault()
    selectTab(nextIndex)
  }

  const items = $derived.by(() =>
    tabs.map((tab, index) => ({
      props: {
        id: `tab-${tab.id}`,
        tabindex: tab.id === currentTabId ? 0 : -1,
        role: 'tab',
        'aria-selected': tab.id === currentTabId ? true : false,
        'aria-controls': `tab-${tab.id}-panel`,
        class: kind === 'tab' ? 'fr-tabs__tab' : 'fr-nav__link',
        onclickcapture: () => (currentTabId = tab.id),
        onkeydowncapture: (event: KeyboardEvent) => handleKeydown(event, index)
      },
      ...tab
    }))
  )
</script>

<div
  {...props}
  class={[
    'fr-tabs',
    { 'tabs-nav': kind === 'nav', 'shadow-none! before:shadow-none!': noBorders },
    props.class
  ]}
>
  <ul class={['fr-tabs__list', { 'px-0!': kind === 'nav' }]} role="tablist" aria-label={label}>
    {#each items as item, i (i)}
      <li role="presentation" class="whitespace-nowrap">
        {#if item.href}
          <a {...item.props} href={item.href}>
            {#if item.icon}<Icon icon={item.icon} size="xs" class="me-2" />{/if}{item.label}
          </a>
        {:else}
          <button {...item.props} type="button">
            {#if item.icon}<Icon icon={item.icon} size="xs" class="me-2" />{/if}{item.label}
          </button>
        {/if}
      </li>
    {/each}
  </ul>
  {#each tabs as item, i (i)}
    {#if item.id === currentTabId}
      <div
        id={`tab-${item.id}-panel`}
        role="tabpanel"
        aria-labelledby={`tab-${item.id}`}
        tabindex="0"
        class={[
          'fr-tabs__panel',
          'fr-tabs__panel--selected',
          { 'px-0! py-5!': noBorders },
          panelClass
        ]}
      >
        {#if item.content}{item.content}{:else}{@render tab?.(item)}{/if}
      </div>
    {/if}
  {/each}
</div>

<style lang="postcss">
  @reference "$css/app.css";

  .fr-tabs__list {
    button,
    a {
      &[aria-selected='true'] {
        --border-active-blue-france: var(--blue-france-main-525);
        color: var(--blue-france-main-525);
      }
    }
  }

  .tabs-nav {
    .fr-tabs__list {
      height: unset !important;
      min-height: unset !important;
    }

    &::before {
      background-color: transparent;
    }
  }

  .fr-nav__link {
    position: relative;
    padding: 12px;
    min-height: unset;

    &[aria-selected='true'] {
      &::before {
        background-color: var(--border-active-blue-france);
      }
    }

    &::before {
      content: '';
      position: absolute;
      top: auto;
      bottom: 0;
      left: 0;
      width: 100%;
      height: 2px;
      margin-top: 0;
      background-color: var(--border-default-grey);
    }
  }
</style>
