<script lang="ts">
  import { Tabs } from '$components/dsfr'
  import SeoHead from '$components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'
  import { Energy, Preferences, RankingTable } from './components'

  const tabs = (
    [
      { id: 'ranking', icon: 'trophy-line' },
      { id: 'energy', icon: 'bar-chart-2-line' },
      { id: 'preferences', icon: 'bar-chart-2-line' },
      { id: 'methodology' }
    ] as const
  ).map((tab) => ({
    ...tab,
    label: m[`ranking.${tab.id}.tabLabel`]()
  }))
</script>

<SeoHead title={m['seo.titles.ranking']()} />

<main class="pb-30 bg-light-grey pt-12">
  <div class="fr-container">
    <h1 class="fr-h3 mb-8!">{m['ranking.title']()}</h1>

    <Tabs {tabs} noBorders kind="nav">
      {#snippet tab({ id })}
        {#if id === 'ranking'}
          <p class="text-[14px]! text-dark-grey mb-12!">
            {@html sanitize(m['ranking.ranking.desc']())}
          </p>

          <RankingTable id="ranking-table" />
        {:else if id === 'energy'}
          <Energy />
        {:else if id === 'preferences'}
          <Preferences />
        {/if}
      {/snippet}
    </Tabs>
  </div>
</main>
