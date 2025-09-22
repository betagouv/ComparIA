<script lang="ts">
  import { Badge, Link, Search, Table } from '$components/dsfr'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import { getVotesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { getModelsContext } from '$lib/models'

  type ColKind =
    | 'rank'
    | 'name'
    | 'elo'
    | 'trust_range'
    | 'total_votes'
    | 'consumption_wh'
    | 'size'
    | 'release'
    | 'organisation'
    | 'license'

  let {
    id,
    initialOrderCol = 'elo',
    includedCols,
    hideTotal = false
  }: {
    id: string
    initialOrderCol?: ColKind
    includedCols?: ColKind[]
    hideTotal?: boolean
  } = $props()

  const NumberFormater = new Intl.NumberFormat(getLocale(), { maximumSignificantDigits: 3 })

  const modelsData = getModelsContext()
  const votesData = getVotesContext()
  const totalVotes = $derived(NumberFormater.format(votesData.count))
  // FIXME retrieve info from backend
  let lastUpdateDate = new Date()
  let selectedModel = $state<string>()
  const selectedModelData = $derived(modelsData.find((m) => m.id === selectedModel))

  const cols = (
    [
      { id: 'rank' },
      { id: 'name', orderable: true },
      { id: 'elo', orderable: true, tooltip: 'FIXME' },
      { id: 'trust_range', tooltip: 'FIXME' },
      { id: 'total_votes', orderable: true },
      { id: 'consumption_wh', orderable: true },
      { id: 'size', orderable: true, tooltip: 'FIXME' },
      { id: 'release', orderable: true },
      { id: 'organisation', orderable: true },
      { id: 'license' }
    ] as const
  )
    .filter((col) => (includedCols ? includedCols.includes(col.id) : true))
    .map((col) => ({
      ...col,
      label: m[`ranking.table.data.cols.${col.id}`]()
    }))

  let orderingCol = $state<ColKind>(initialOrderCol)
  let search = $state('')

  function sortIfDefined(a: Record<string, any>, b: Record<string, any>, key: string) {
    if (a[key] !== undefined && b[key] !== undefined) return b[key] - a[key]
    if (a[key] !== undefined) return -1
    if (b[key] !== undefined) return 1
    return a.id.localeCompare(b.id)
  }

  const rows = $derived.by(() => {
    const models = modelsData.filter((m) => !!m.elo).sort((a, b) => sortIfDefined(a, b, 'elo'))
    const highestElo = models[0].elo!
    const lowestElo = models.reduce((a, m) => (m?.elo && m.elo < a ? m.elo : a), highestElo)
    const highestConso = models.reduce(
      (a, m) => (m?.consumption_wh && m.consumption_wh > a ? m.consumption_wh : a),
      0
    )

    return models.map((model, i) => {
      const [month, year] = model.release_date.split('/')

      return {
        ...model,
        release_date: new Date([month, '01', year].join('/')),
        rank: i + 1,
        eloRangeWidth: model.elo
          ? Math.ceil(((model.elo - lowestElo) / (highestElo - lowestElo)) * 100)
          : null,
        consoRangeWidth: model.consumption_wh
          ? Math.ceil((model.consumption_wh / highestConso) * 100)
          : null,
        search: (['id', 'simple_name', 'organisation'] as const)
          .map((key) => model[key].toLowerCase())
          .join(' ')
      }
    })
  })

  const sortedRows = $derived.by(() => {
    const _search = search.toLowerCase()

    return rows
      .filter((m) => (!_search ? true : m.search.includes(_search)))
      .sort((a, b) => {
        switch (orderingCol) {
          case 'name':
            return a.id.localeCompare(b.id)
          case 'elo':
          case 'total_votes':
            return sortIfDefined(a, b, orderingCol)
          case 'consumption_wh':
            return sortIfDefined(b, a, orderingCol)
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
  })
</script>

<Table {id} {cols} rows={sortedRows} bind:orderingCol caption={m['ranking.title']()} hideCaption>
  {#snippet header()}
    <div class="flex flex-wrap items-center gap-5">
      {#if !hideTotal}
        <div class="flex gap-5">
          <div class="cg-border rounded-sm! bg-white px-4 py-2">
            <strong>{m['ranking.table.totalModels']()}</strong>
            <span class="text-grey">{rows.length}</span>
          </div>

          <div class="cg-border rounded-sm! bg-white px-4 py-2">
            <strong>{m['ranking.table.totalVotes']()}</strong>
            <span class="text-grey">{totalVotes}</span>
          </div>
        </div>
      {/if}

      <div class="fr-table__detail mb-0! flex gap-5">
        <p class="mb-0! text-[14px]!">
          {m['ranking.table.lastUpdate']({ date: lastUpdateDate.toLocaleDateString() })}
        </p>

        <!-- FIXME 404 -->
        <Link
          native={false}
          href="/data/ranking.csv"
          download="true"
          text={m['ranking.table.downloadData']()}
          icon="download-line"
          iconPos="right"
          class="text-[14px]!"
        />
      </div>
    </div>

    <Search id="model-search" bind:value={search} label={m['ranking.table.search']()} />
  {/snippet}

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
      <a
        href="#{model.id}"
        data-fr-opened="false"
        aria-controls="{id}-modal-model"
        class="text-black!"
        onclick={() => (selectedModel = model.id)}>{model.id}</a
      >
    {:else if col.id === 'size'}
      <strong>{model.friendly_size}</strong> -
      {#if model.distribution === 'api-only'}
        <span class="text-xs">(est.)</span>
      {:else}
        {model.params} Mds
      {/if}
    {:else if col.id === 'release'}
      {`${model.release_date.getMonth() + 1}/${model.release_date.getFullYear().toString().slice(2)}`}
    {:else if col.id === 'license'}
      <Badge {...model.badges.license} size="xs" noTooltip />
    {:else if model[col.id] === undefined}
      <span class="text-xs">{m['words.NA']()}</span>
    {:else if col.id === 'elo'}
      <div
        class="cg-border text-info rounded-sm! relative max-w-[100px]"
        style="--range-width: {model.eloRangeWidth}%"
      >
        <div class="bg-light-info w-(--range-width) absolute z-0 h-full rounded-sm"></div>
        <span class="z-1 relative p-1 text-xs font-bold">{model.elo}</span>
      </div>
    {:else if col.id === 'trust_range'}
      +{model.trust_range![0]}/-{model.trust_range![1]}
    {:else if col.id === 'consumption_wh'}
      {model.consumption_wh} Wh
      <div class="max-w-[80px]" style="--range-width: {model.consoRangeWidth}%">
        <div class="rounded-xs bg-info w-(--range-width) h-[4px]"></div>
      </div>
    {:else}
      {model[col.id]}
    {/if}
  {/snippet}
</Table>

<ModelInfoModal model={selectedModelData} modalId="{id}-modal-model" />
