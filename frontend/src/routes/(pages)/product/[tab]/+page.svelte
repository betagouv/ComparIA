<script lang="ts">
  import SeoHead from '$components/SEOHead.svelte'
  import { Tabs } from '$lib/components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { Comparator, FAQ, History, Partners, Problem } from './components'

  const { data } = $props()

  const tabs = [
    { id: 'comparator', href: '/product/comparator', label: 'Le comparateur' },
    { id: 'problem', href: '/product/problem', label: 'Le problème initial' },
    { id: 'history', href: '/product/history', label: 'Historique du projet' },
    { id: 'faq', href: '/product/faq', label: 'FAQ' },
    { id: 'partners', href: '/product/partners', label: 'Partenaires' }
  ] as const
</script>

<SeoHead title={m[`seo.titles.${data.tab}`]()} />

<main class="pb-30 bg-light-grey pt-12">
  <div class="fr-container">
    <h1 class="fr-h3 mb-10!">{m['product.title']()}</h1>

    <Tabs {tabs} initialId={data.tab} label={m['product.title']()} panelClass="px-4! md:p-10!">
      {#snippet tab({ id })}
        {#if id === 'comparator'}
          <Comparator />
        {:else if id === 'problem'}
          <Problem />
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
