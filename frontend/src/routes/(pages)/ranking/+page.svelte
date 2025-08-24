<script lang="ts">
  import { Table } from '$components/dsfr'
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

    <Table caption={m['ranking.title']()} {cols} rows={modelsData} bind:orderingCol hideCaption>
      {#snippet cell(model, col)}
        {model[col.id]}
      {/snippet}
    </Table>
  </div>
</main>
