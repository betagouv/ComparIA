<script lang="ts">
  import { Accordion, AccordionGroup, Alert, Segmented } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'
  import { EnergyGraph, RankingTable } from '.'

  const views = ([{ id: 'graph' }, { id: 'table' }] as const).map((view) => ({
    ...view,
    value: view.id,
    label: m[`ranking.energy.views.${view.id}.tabLabel`]()
  }))

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

  let view = $state<(typeof views)[number]['id']>('graph')
</script>

<div id="ranking-energy">
  <h2 class="fr-h6 text-primary! mb-4!">{m['ranking.energy.title']()}</h2>
  <p class="mb-8! text-[14px]! text-dark-grey">{m['ranking.energy.desc']()}</p>

  <div class="rounded bg-white p-8">
    <div class="text-center">
      <Segmented
        id="energy-view"
        bind:value={view}
        legend={m['ranking.energy.views.legend']()}
        options={views}
        hideLegend
        size="sm"
      />
      <h3 class="text-lg! mt-3! mb-1!">{m['ranking.energy.views.title']()}</h3>

      {#if view === 'graph'}
        <p class="text-grey! text-sm!">{m['ranking.energy.views.graph.desc']()}</p>
      {/if}
    </div>

    {#if view === 'graph'}
      <EnergyGraph />

      <Alert title={m['ranking.energy.views.graph.infos.title']()} class="mb-10">
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
    {:else}
      <RankingTable
        id="energy-table"
        initialOrderCol="consumption_wh"
        includedCols={['name', 'elo', 'consumption_wh', 'size', 'organisation', 'license']}
        hideTotal
      />
    {/if}
  </div>
</div>
