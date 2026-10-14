<script lang="ts">
  import { page } from '$app/state'
  import type { ResolvedPathname } from '$app/types'
  import TabNav from '$components/dsfr/TabNav.svelte'
  import { PageLayout } from '$components/layout'
  import { m } from '$lib/i18n/messages'
  import { setVoteTagsContext } from '$lib/voteTags'
  import type { LayoutProps } from './$types'
  import { FilterBar } from './components'
  import { SHARED_FILTERS, pick, withQuery } from './filters'

  let { data, children }: LayoutProps = $props()

  // Tags are shown with the arena's own emoji and words.
  // svelte-ignore state_referenced_locally
  setVoteTagsContext(data.voteTags)

  const shared = $derived(pick(page.url.searchParams, SHARED_FILTERS))
  const links = $derived(
    [
      { id: 'apercu', icon: 'i-ri-dashboard-line', label: m['admin.activity.tabs.overview']() },
      {
        id: 'conversations',
        icon: 'i-ri-chat-3-line',
        label: m['admin.activity.tabs.conversations']()
      }
    ].map((link) => ({
      ...link,
      href: withQuery(`/admin/activite/${link.id}`, shared) as ResolvedPathname
    }))
  )
</script>

<PageLayout
  seoTitle={m['admin.activity.title']()}
  title={m['admin.activity.title']()}
  subtitle={m['admin.activity.subTitle']()}
>
  <TabNav {links} class="mb-5" />

  {#if !page.params.id}
    <FilterBar options={data.options} />
  {/if}

  {@render children()}
</PageLayout>

<style>
  /* Both tabs' filters: selects and dates as quiet pills in one toolbar row,
     their names inside the first option or in the accessible label. */
  :global(.activity-filters .fr-select),
  :global(.activity-filters .fr-input-group .fr-input) {
    margin-top: 0;
    width: auto;
    max-width: 12rem;
    padding-top: 0.375rem;
    padding-bottom: 0.375rem;
    font-size: 0.875rem;
    border-radius: 0.5rem;
    box-shadow: inset 0 0 0 1px var(--border-default-grey);
    background-color: var(--background-default-grey);
  }
</style>
