<script lang="ts">
  import { Badge, Table } from '$components/dsfr'
  import SeoHead from '$lib/components/SEOHead.svelte'
  import { m } from '$lib/i18n/messages'
  import { getModelsContext } from '$lib/models'
  import { propsToAttrs, sanitize } from '$lib/utils/commons'

  const modelsData = getModelsContext()

  const cols = (
    [
      { id: 'rank' },
      { id: 'name', orderable: true },
      { id: 'elo', orderable: true, tooltip: 'FIXME' },
      { id: 'trust', tooltip: 'FIXME' },
      { id: 'votes', orderable: true },
      { id: 'consumption', orderable: true },
      { id: 'size', orderable: true, tooltip: 'FIXME' },
      { id: 'release', orderable: true },
      { id: 'organisation', orderable: true },
      { id: 'license' }
    ] as const
  ).map((col) => ({
    ...col,
    label: m[`ranking.table.data.cols.${col.id}`]()
  }))

  let orderingCol = $state<(typeof cols)[number]['id']>('elo')

  const rows = $derived.by(() => {
    return modelsData.map((m, i) => {
      // FIXME replace mock with real data
      const conso = Math.round(Math.random() * 10)
      const [month, year] = m.release_date.split('/')
      return {
        ...m,
        release_date: new Date([month, '01', year].join('/')),
        rank: i + 1,
        elo: Math.round(Math.random() * 10),
        trust: `+${Math.round(Math.random() * 10)}/-${Math.round(Math.random() * 10)}`,
        votes: Math.round(Math.random() * 1000),
        consumption: conso > 5 ? null : conso
      }
    })
  })

  const sortedRows = $derived.by(() => {
    return rows
      .sort((a, b) => {
        switch (orderingCol) {
          case 'name':
            return a.id.localeCompare(b.id)
          case 'elo':
            return b.elo - a.elo
          case 'votes':
            return b.votes - a.votes
          case 'consumption':
            if (a.consumption !== null && b.consumption !== null)
              return b.consumption - a.consumption
            if (a.consumption !== null) return -1
            if (b.consumption !== null) return 1
            return 0
          case 'size':
            return b.params - a.params
          case 'release':
            return Number(b.release_date) - Number(a.release_date)
          case 'organisation':
            return a.organisation.localeCompare(b.organisation)
          default:
            return a.rank - b.rank
        }
      })
      .filter(() => true)
  })
</script>

<SeoHead title={m['seo.titles.ranking']()} />

<main class="pb-30 bg-light-grey pt-12">
  <div class="fr-container">
    <h1 class="fr-h3 mb-10!">{m['ranking.title']()}</h1>

    <p>
      {@html sanitize(
        m['ranking.desc']({
          linkProps: propsToAttrs({ href: '#FIXME', class: 'text-primary!' })
        })
      )}
    </p>

    <Table caption={m['ranking.title']()} {cols} rows={sortedRows} bind:orderingCol hideCaption>
      {#snippet cell(model, col)}
        {#if col.id === 'rank'}
          <span class="font-medium">{model.rank}</span>
        {:else if col.id === 'name'}
          <img
            src="/orgs/ai/{model.icon_path}"
            alt={model.organisation}
            width="20"
            class="me-1 inline-block"
          />
          {model.id}
        {:else if col.id === 'elo'}
          {model.elo}
        {:else if col.id === 'trust'}
          {model.trust}
        {:else if col.id === 'votes'}
          {model.votes}
        {:else if col.id === 'consumption'}
          {#if model.consumption === null}
            <span class="text-xs">N/A</span>
          {:else}
            {model.consumption}
          {/if}
        {:else if col.id === 'size'}
          <strong>{model.friendly_size}</strong> -
          {#if model.distribution === 'api-only'}
            <span class="text-xs">(est.)</span>
          {:else}
            {model.params} Mds
          {/if}
        {:else if col.id === 'release'}
          {`${model.release_date.getMonth() + 1}/${model.release_date.getFullYear().toString().slice(2)}`}
        {:else if col.id === 'organisation'}
          {model.organisation}
        {:else if col.id === 'license'}
          <Badge {...model.badges.license} size="xs" noTooltip />
        {/if}
      {/snippet}
    </Table>
  </div>
</main>
