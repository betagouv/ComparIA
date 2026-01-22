<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Link, Table } from '$components/dsfr'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import { getVotesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { getModelsContext, getModelsWithDataContext, type Archs } from '$lib/models'
  import { sortIfDefined } from '$lib/utils/data'

  type ColKind =
    | 'rank'
    | 'name'
    | 'elo'
    | 'trust_range'
    | 'n_match'
    | 'consumption_wh'
    | 'size'
    | 'arch'
    | 'release'
    | 'organisation'
    | 'license'

  let {
    id,
    initialOrderCol = 'elo',
    initialOrderMethod = 'descending',
    includedCols,
    onDownloadData,
    hideTotal = false,
    raw = false,
    filterProprietary = false,
    useStyleControl = false
  }: {
    id: string
    initialOrderCol?: ColKind
    initialOrderMethod?: 'ascending' | 'descending'
    includedCols?: ColKind[]
    onDownloadData: () => void
    hideTotal?: boolean
    raw?: boolean
    filterProprietary?: boolean
    useStyleControl?: boolean
  } = $props()

  const NumberFormater = new Intl.NumberFormat(getLocale(), { maximumSignificantDigits: 3 })

  const votesData = getVotesContext()
  const totalVotes = $derived(NumberFormater.format(votesData.count))
  const modelsContext = getModelsWithDataContext()
  const { lastUpdateDate } = modelsContext

  let selectedModel = $state<string>()
  const selectedModelData = $derived(modelsContext.models.find((m) => m.id === selectedModel))

  // Transform data based on style control toggle
  // When enabled, use style_controlled values (no trust_range filter for style-controlled)
  const data = $derived.by(() => {
    if (!useStyleControl) {
      return modelsContext.models
    }

    // For style control, we need to start from ALL models and filter differently
    const allModels = getModelsContext().models

    // Filter for models with style_controlled data (no trust_range check for style-controlled)
    const filtered = allModels.filter((model) => {
      if (!model.data?.style_controlled) return false
      if (!model.prefs) return false
      return true
    })

    return filtered.map((model) => {
      const sc = model.data!.style_controlled!

      return {
        ...model,
        data: {
          ...model.data,
          elo: sc.elo,
          rank: sc.rank,
          score_p2_5: sc.score_p2_5,
          score_p97_5: sc.score_p97_5,
          rank_p2_5: sc.rank_p2_5,
          rank_p97_5: sc.rank_p97_5,
          trust_range: sc.trust_range
        }
      }
    })
  })

  const cols = (
    [
      { id: 'rank', tooltip: m['ranking.table.data.tooltips.rank']() },
      { id: 'name' },
      { id: 'elo', tooltip: m['ranking.table.data.tooltips.elo']() },
      { id: 'trust_range', tooltip: m['ranking.table.data.tooltips.trust_range']() },
      { id: 'n_match' },
      { id: 'consumption_wh', tooltip: m['ranking.table.data.tooltips.consumption_wh']() },
      { id: 'size', tooltip: m['ranking.table.data.tooltips.size']() },
      { id: 'arch', tooltip: m['ranking.table.data.tooltips.arch']() },
      { id: 'release' },
      { id: 'organisation' },
      { id: 'license' }
    ] as const
  )
    .filter((col) => (includedCols ? includedCols.includes(col.id) : true))
    .map((col) => ({
      ...col,
      label: m[`ranking.table.data.cols.${col.id}`](),
      orderable: true,
      colHeaderClass: raw ? 'bg-white! border-b-1 border-[--border-contrast-grey]' : ''
    }))

  let orderingCol = $state(initialOrderCol)
  let orderingMethod = $state(initialOrderMethod)
  let search = $state('')

  $effect(() => {
    if (orderingCol === undefined) {
      orderingCol = initialOrderCol
      orderingMethod = initialOrderMethod
    }
  })

  const rows = $derived.by(() => {
    // Explicit dependency to ensure reactivity when style control toggles
    const _ = useStyleControl
    const models = data
      .filter((m) => {
        if (filterProprietary) return m.license !== 'proprietary'
        return true
      })
      .sort((a, b) => sortIfDefined(a.data, b.data, 'elo'))

    if (models.length === 0) return []

    const highestElo = models[0].data.elo!
    const lowestElo = models.reduce((a, m) => (m.data.elo < a ? m.data.elo : a), highestElo)
    const highestConso = models.reduce((a, m) => (m.consumption_wh > a ? m.consumption_wh : a), 0)

    return models.map((model) => {
      const [month, year] = model.release_date.split('/')

      return {
        ...model,
        arch: (model.license === 'proprietary' ? 'na' : model.arch) as Archs,
        release_date: new Date([month, '01', year].join('/')),
        eloRangeWidth: Math.ceil(((model.data.elo - lowestElo) / (highestElo - lowestElo)) * 100),
        consoRangeWidth: Math.ceil((model.consumption_wh / highestConso) * 100)
      }
    })
  })

  const sortedRows = $derived.by(() => {
    // Include useStyleControl to force re-sort when toggled
    const _ = useStyleControl
    const _search = search.toLowerCase()

    return rows
      .filter((m) => (!_search ? true : m.search.includes(_search)))
      .sort((ma, mb) => {
        const [a, b] = orderingMethod === 'ascending' ? [mb, ma] : [ma, mb]

        switch (orderingCol) {
          case 'name':
            return a.id.localeCompare(b.id)
          case 'elo':
          case 'n_match':
            return sortIfDefined(a.data, b.data, orderingCol)
          case 'consumption_wh': {
            const aProprietary = a.license === 'proprietary'
            const bProprietary = b.license === 'proprietary'
            if (aProprietary && bProprietary) return a.id.localeCompare(b.id)
            if (aProprietary) return orderingMethod === 'ascending' ? -1 : 1
            if (bProprietary) return orderingMethod === 'ascending' ? 1 : -1
            return b.consumption_wh - a.consumption_wh
          }
          case 'trust_range': {
            const aCount = a.data.trust_range[0] + a.data.trust_range[1]
            const bCount = b.data.trust_range[0] + b.data.trust_range[1]
            if (aCount === bCount) return a.data.rank - b.data.rank
            return aCount - bCount
          }
          case 'size':
            return b.params - a.params
          case 'release':
            return Number(b.release_date) - Number(a.release_date)
          case 'arch':
          case 'organisation':
          case 'license':
            return a[orderingCol].localeCompare(b[orderingCol])
          default:
            return a.data.rank - b.data.rank
        }
      })
  })
</script>

<Table
  {id}
  {cols}
  rows={sortedRows}
  bind:orderingCol
  bind:orderingMethod
  bind:search
  searchLabel={m['actions.searchModel']()}
  caption={m['ranking.title']()}
  hideCaption
>
  {#snippet headerLeft()}
    {#if !hideTotal}
      <div class="gap-5 flex">
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

    <div class="fr-table__detail mb-0! gap-3 md:flex-row md:gap-5 flex flex-col">
      <p class="mb-0! text-[14px]!">
        {m['ranking.table.lastUpdate']({ date: lastUpdateDate })}
      </p>

      <Link
        native={raw}
        href="#"
        download="true"
        text={m['actions.downloadData']()}
        icon="download-line"
        iconPos="right"
        class={['text-[14px]!', { 'text-grey!': raw }]}
        onclick={() => onDownloadData()}
      />
    </div>
  {/snippet}

  {#snippet cell(model, col)}
    {#if col.id === 'rank'}
      <span class="font-medium">{model.data.rank}</span>
    {:else if col.id === 'name'}
      <div
        class="sm:max-w-none sm:overflow-visible max-w-[205px] overflow-hidden overflow-ellipsis"
      >
        <AILogo
          iconPath={model.icon_path}
          alt={model.organisation}
          class="me-1 inline-block align-middle"
        />
        <a
          href="#{model.id}"
          data-fr-opened="false"
          aria-controls="{id}-modal-model"
          class="text-black!"
          onclick={() => (selectedModel = model.id)}>{model.id}</a
        >
      </div>
    {:else if col.id === 'size'}
      <strong>{model.friendly_size}</strong> -
      {#if model.distribution === 'api-only'}
        <span class="text-xs">{m['ranking.table.data.estimation']()}</span>
      {:else}
        {m['ranking.table.data.billions']({ count: model.params })}
      {/if}
    {:else if col.id === 'release'}
      {`${model.release_date.getMonth() + 1}/${model.release_date.getFullYear().toString().slice(2)}`}
    {:else if col.id === 'license'}
      {#if raw}
        {model.badges.license.text}
      {:else}
        <Badge {...model.badges.license} size="xs" noTooltip />
      {/if}
    {:else if col.id === 'elo'}
      {#if raw}
        {model.data.elo}
      {:else}
        <div
          class="cg-border rounded-sm! text-info relative max-w-[100px]"
          style="--range-width: {model.eloRangeWidth}%"
        >
          <div class="bg-light-info rounded-sm absolute z-0 h-full w-[--range-width]"></div>
          <span class="p-1 text-xs font-bold relative z-1">{model.data.elo}</span>
        </div>
      {/if}
    {:else if col.id === 'trust_range'}
      -{model.data.trust_range![1]}/+{model.data.trust_range![0]}
    {:else if col.id === 'consumption_wh'}
      {#if model.license === 'proprietary'}
        <span class="text-xs text-[--grey-625-425]">{m['words.NA']()}</span>
      {:else}
        {model.consumption_wh} Wh
        {#if !raw}
          <div class="max-w-[80px]" style="--range-width: {model.consoRangeWidth}%">
            <div class="rounded-xs bg-info h-[4px] w-[--range-width]"></div>
          </div>
        {/if}
      {/if}
    {:else if col.id === 'arch'}
      {m[`generated.archs.${model.arch}.name`]()}
    {:else if col.id === 'n_match'}
      {model.data.n_match}
    {:else if col.id === 'organisation'}
      {model.organisation}
    {/if}
  {/snippet}
</Table>

<ModelInfoModal model={selectedModelData} modalId="{id}-modal-model" />
