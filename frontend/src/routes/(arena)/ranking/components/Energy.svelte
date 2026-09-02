<script lang="ts">
  import { Icon } from '$components/dsfr'
  import { getVotesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { applyStyleControl, getModelsWithDataContext, rankClassSpans } from '$lib/models'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'
  import { EnergyGraph, RankingTable } from '.'

  let { onDownloadData }: { onDownloadData: () => void } = $props()

  const { lastUpdateDate, commons, models: modelsData } = getModelsWithDataContext()
  const votesData = getVotesContext()
  const rankingRows = $derived(applyStyleControl(modelsData))
  const rankingCommons = $derived({
    ...commons,
    rankClasses: rankClassSpans(rankingRows.map((m) => m.data))
  })
</script>

<div id="ranking-energy">
  <h2 class="fr-h6 mb-4! text-primary!">{m['ranking.energy.title']()}</h2>
  <p class="mb-8! text-dark-grey text-[14px]!">
    {@html sanitize(
      m['ranking.energy.desc']({
        linkProps: externalLinkProps('https://ecologits.ai/latest/')
      })
    )}
  </p>

  <div class="gap-8 flex flex-col">
    <section class="cg-border bg-white p-4 md:p-10">
      <div class="mb-10 text-center">
        <h3 class="mt-3! mb-0! text-lg!">{m['ranking.energy.views.graph.title']()}</h3>
        <p class="text-sm! text-grey!">{m['ranking.energy.views.graph.desc']()}</p>
      </div>

      <EnergyGraph />

      <p class="mt-6! mb-0! text-sm! text-center">
        <a href="#energy-table" class="fr-link fr-link--sm">{m['a11y.graphAsTable']()}</a>
      </p>
    </section>

    <div class="gap-8 md:flex-row flex flex-col">
      <section class="cg-border bg-white p-4 md:p-10 basis-1/2">
        <h3 class="text-lg! gap-3 flex items-center">
          <Icon icon="i-ri-search-eye-line" size="lg" block class="text-yellow" />
          <span>
            {m['ranking.energy.views.methodo.1.title']()}
            <span class="font-normal!">{m['ranking.energy.views.methodo.1.subTitle']()}</span>
          </span>
        </h3>

        <ul class="text-grey text-[14px]">
          {#each ['1', '2', '3'] as const as n (n)}
            <li>{@html sanitize(m[`ranking.energy.views.methodo.1.list.${n}`]())}</li>
          {/each}
        </ul>
      </section>

      <section class="cg-border bg-white p-4 md:p-10 basis-1/2">
        <h3 class="text-lg! gap-3 flex items-center">
          <Icon icon="i-ri-database-2-line" size="lg" block class="text-primary" />
          {m['ranking.energy.views.methodo.2.title']()}
        </h3>

        <p class="text-grey text-[14px]!">{m['ranking.energy.views.methodo.2.descs.1']()}</p>
        <p class="text-grey text-[14px]!">{m['ranking.energy.views.methodo.2.descs.2']()}</p>
      </section>
    </div>

    <section class="cg-border bg-white p-4 md:p-10">
      <h3 class="text-lg! gap-3 flex items-center">
        <Icon icon="i-ri-leaf-line" size="lg" block class="text-green" />
        {m['ranking.energy.views.methodo.3.title']()}
      </h3>

      <p class="text-grey text-[14px]!">
        {@html sanitize(
          m['ranking.energy.views.methodo.3.descs.1']({
            ecoLinkProps: externalLinkProps('https://ecologits.ai/latest/'),
            genaiLinkProps: externalLinkProps('https://genai-impact.org/')
          })
        )}
      </p>
      <p class="text-grey text-[14px]!">
        {@html sanitize(m['ranking.energy.views.methodo.3.descs.2']())}
      </p>
      <p class="text-grey text-[14px]!">{m['ranking.energy.views.methodo.3.descs.3']()}</p>
      <p class="mb-0! text-grey text-[14px]!">{m['ranking.energy.views.methodo.3.descs.4']()}</p>
    </section>

    <section class="cg-border bg-white p-4 md:p-10">
      <h3 class="mb-0! text-lg!">{m['ranking.energy.views.table.title']()}</h3>
      <RankingTable
        id="energy-table"
        caption={m['ranking.energy.views.table.title']()}
        models={rankingRows}
        commons={rankingCommons}
        {lastUpdateDate}
        totalVotes={votesData.count}
        initialOrderCol="consumption"
        initialOrderMethod="ascending"
        includedCols={['name', 'elo', 'consumption', 'size', 'arch', 'organisation', 'license']}
        hideTotal
        raw
        filterProprietary
        {onDownloadData}
      />
    </section>
  </div>
</div>
