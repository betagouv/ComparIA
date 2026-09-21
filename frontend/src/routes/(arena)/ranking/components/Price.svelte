<script lang="ts">
  import { Icon } from '$components/dsfr'
  import { getVotesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { applyStyleControl, getModelsWithDataContext, rankClassSpans } from '$lib/models'
  import { sanitize } from '$lib/utils/commons'
  import { PriceGraph, RankingTable } from '.'

  let { onDownloadData }: { onDownloadData: () => void } = $props()

  const { lastUpdateDate, commons, models: modelsData } = getModelsWithDataContext()
  const votesData = getVotesContext()
  const rankingRows = $derived(applyStyleControl(modelsData))
  const rankingCommons = $derived({
    ...commons,
    rankClasses: rankClassSpans(rankingRows.map((llm) => llm.data))
  })
</script>

<div id="ranking-price">
  <h2 class="fr-h6 mb-4! text-primary!">{m['ranking.price.title']()}</h2>
  <p class="mb-8! text-dark-grey text-[14px]!">
    {@html sanitize(m['ranking.price.desc']({ currency: commons.currency.code }))}
  </p>

  <div class="gap-8 flex flex-col">
    <section class="cg-border bg-white p-4 md:p-10">
      <div class="mb-10 text-center">
        <h3 class="mt-3! mb-0! text-lg!">{m['ranking.price.views.graph.title']()}</h3>
        <p class="text-sm! text-grey!">{m['ranking.price.views.graph.desc']()}</p>
      </div>

      <PriceGraph />

      <p class="mt-6! mb-0! text-sm! text-center">
        <a href="#price-table" class="fr-link fr-link--sm">{m['a11y.graphAsTable']()}</a>
      </p>
    </section>

    <section class="cg-border bg-white p-4 md:p-10">
      <h3 class="text-lg! gap-3 flex items-center">
        <Icon icon="i-ri-search-eye-line" size="lg" block class="text-yellow" />
        <span>
          {m['ranking.price.views.methodo.title']()}
          <span class="font-normal!">{m['ranking.price.views.methodo.subTitle']()}</span>
        </span>
      </h3>

      <ul class="text-grey text-[14px]">
        {#each ['1', '2', '3'] as const as n (n)}
          <li>{@html sanitize(m[`ranking.price.views.methodo.list.${n}`]())}</li>
        {/each}
      </ul>
    </section>

    <section class="cg-border bg-white p-4 md:p-10">
      <h3 class="mb-0! text-lg!">{m['ranking.price.views.table.title']()}</h3>
      <RankingTable
        id="price-table"
        caption={m['ranking.price.views.table.title']()}
        models={rankingRows}
        commons={rankingCommons}
        {lastUpdateDate}
        totalVotes={votesData.count}
        initialOrderCol="price_out"
        initialOrderMethod="ascending"
        includedCols={['name', 'elo', 'price_out', 'price_in', 'organisation', 'license']}
        hideTotal
        raw
        {onDownloadData}
      />
    </section>
  </div>
</div>
