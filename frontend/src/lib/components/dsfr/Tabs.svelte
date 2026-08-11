<script
  lang="ts"
  generics="T extends { id: string; label: string; href?: string; content?: string, icon?: string }"
>
  import { resolve } from '$app/paths'
  import { untrack, type Snippet } from 'svelte'
  import type { ClassValue, SvelteHTMLElements } from 'svelte/elements'
  import { Icon } from '.'

  // resolve() is typed for routes known at compile time, one literal per call. Tabs
  // takes its hrefs as plain strings, so the generic signature can never match.
  const resolveHref = resolve as (href: string) => string

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

  let currentTabId = $state(untrack(() => initialId))

  function selectTab(index: number) {
    const tab = tabs[index]
    if (!tab) return
    currentTabId = tab.id
    document.getElementById(`tab-${tab.id}`)?.focus()
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
        onclick: () => (currentTabId = tab.id),
        onkeydown: (event: KeyboardEvent) => handleKeydown(event, index)
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
          <a {...item.props} href={resolveHref(item.href)}>
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
    <div
      id={`tab-${item.id}-panel`}
      role="tabpanel"
      aria-labelledby={`tab-${item.id}`}
      tabindex="0"
      hidden={item.id !== currentTabId}
      class={[
        'fr-tabs__panel',
        {
          'fr-tabs__panel--selected': item.id === currentTabId,
          'px-0! py-5!': noBorders,
          'visibility-none! transition-none!': item.href && item.id !== currentTabId
        },
        panelClass
      ]}
    >
      {#if item.content}{item.content}{:else}{@render tab?.(item)}{/if}
    </div>
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
