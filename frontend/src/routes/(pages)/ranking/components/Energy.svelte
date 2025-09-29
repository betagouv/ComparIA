<script lang="ts">
  import { Accordion, AccordionGroup, Alert } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import type { BotModel } from '$lib/models'
  import { sanitize } from '$lib/utils/commons'
  import { EnergyGraph, RankingTable } from '.'

  let { data, onDownloadData }: { data: BotModel[]; onDownloadData: () => void } = $props()

  const faq = [
    {
      id: 'faq-1',
      title: m['faq.ecology.questions.1.title'](),
      desc: m['faq.ecology.questions.1.desc']()
    },
    {
      id: 'faq-2',
      title: m['ranking.energy.views.graph.faq.1.title'](),
      desc: m['ranking.energy.views.graph.faq.1.desc']()
    }
  ] as const
</script>

<div id="ranking-energy">
  <h2 class="fr-h6 text-primary! mb-1!">{m['ranking.energy.title']()}</h2>
  <p class="mb-8! text-[14px]! text-dark-grey">{m['ranking.energy.desc']()}</p>

  <div class="rounded bg-white p-8">
    <section>
      <div class="mb-10 text-center">
        <h3 class="text-lg! mt-3! mb-0!">{m['ranking.energy.views.graph.title']()}</h3>
        <p class="text-grey! text-sm!">{m['ranking.energy.views.graph.desc']()}</p>
      </div>

      <EnergyGraph {data} />

      <Alert title={m['ranking.energy.views.graph.infos.title']()} class="mb-10 mt-12">
        <ul>
          {#each ['1', '2', '3'] as const as n}
            <li>{m[`ranking.energy.views.graph.infos.list.${n}`]()}</li>
          {/each}
        </ul>
      </Alert>

      <AccordionGroup>
        {#each faq as q (q.id)}
          <Accordion id={q.id} label={q.title}>
            {@html sanitize(q.desc)}
          </Accordion>
        {/each}
      </AccordionGroup>
    </section>

    <section class="mt-25">
      <h3 class="text-lg! mb-0!">{m['ranking.energy.views.table.title']()}</h3>
      <RankingTable
        id="energy-table"
        {data}
        includedCols={['name', 'elo', 'consumption_wh', 'size', 'organisation', 'license']}
        hideTotal
        {onDownloadData}
      />
    </section>
  </div>
</div>
