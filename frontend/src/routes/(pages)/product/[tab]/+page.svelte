<script lang="ts">
  import SeoHead from '$components/SEOHead.svelte'
  import { Tabs } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { Community, Comparator, FAQ, History, Partners, Problem } from './components'

  const { data } = $props()
  const locale = getLocale()
  const isFr = $derived(['fr', 'en'].includes(locale))

  const tabs = (
    [
      { id: 'comparator' },
      { id: 'problem' },
      { id: 'community' },
      { id: 'history' },
      { id: 'faq' },
      { id: 'partners' }
    ] as const
  ).map((tab) => ({
    ...tab,
    href: `/product/${tab.id}`,
    label: m[`product.${tab.id}.tabLabel`]()
  }))
</script>

<SeoHead title={m[`seo.titles.${data.tab}`]()} />

<main class={['bg-light-grey pt-12 pb-30', isFr ? 'next' : 'prev']}>
  <div class="fr-container">
    <h1 class="fr-h3 mb-10!">{m['product.title']()}</h1>

    <Tabs
      {tabs}
      initialId={data.tab}
      label={m['product.title']()}
      panelClass="bg-white px-4! md:p-10!"
    >
      {#snippet tab({ id })}
        {#if id === 'comparator'}
          <Comparator />
        {:else if id === 'problem'}
          <Problem />
        {:else if id === 'community'}
          <Community />
        {:else if id === 'history'}
          <History />
        {:else if id === 'faq'}
          <FAQ />
        {:else if id === 'partners'}
          <Partners />
        {/if}
      {/snippet}
    </Tabs>
  </div>
</main>

<style>
  /* FIXME remove when avaible */
  :global(main.prev #tab-community, main.prev #tab-history) {
    display: none;
  }

  :global(main.next #tab-partners) {
    display: none;
  }
</style>
