<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Link, Table, Toggle, Tooltip } from '$components/dsfr'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import type { Archs } from '$lib/generated/constants'
  import { getVotesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import {
    applyStyleControl,
    getModelsWithDataContext,
    rankClassLabel,
    rankClassSpans
  } from '$lib/models'
  import { sortIfDefined } from '$lib/utils/data'

  type ColKind =
    | 'rank'
    | 'name'
    | 'elo'
    | 'trust_range'
    | 'n_match'
    | 'consumption'
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
    filterProprietary = false
  }: {
    id: string
    initialOrderCol?: ColKind
    initialOrderMethod?: 'ascending' | 'descending'
    includedCols?: ColKind[]
    onDownloadData: () => void
    hideTotal?: boolean
    raw?: boolean
    filterProprietary?: boolean
  } = $props()

  const NumberFormater = new Intl.NumberFormat(getLocale(), { maximumSignificantDigits: 3 })

  const votesData = getVotesContext()
  const totalVotes = $derived(NumberFormater.format(votesData.count))
  const { lastUpdateDate, commons, models: baseModels } = getModelsWithDataContext()
  const data = $derived(applyStyleControl(baseModels))
  let selectedModel = $state<string>()
  const selectedModelData = $derived(data.find((m) => m.id === selectedModel))
  // The class spans in the context describe the style-controlled fit. The
  // modal has to describe the fit on screen, so they are derived from it.
  const activeCommons = $derived({
    ...commons,
    rankClasses: rankClassSpans(data.map((m) => m.data))
  })

  // Escape hatch back to numbered ranks. Deliberately not persisted: classes
  // are the honest default and a sticky toggle would quietly undo that.
  let showRanks = $state(false)

  const cols = $derived(
    (
      [
        { id: 'rank', tooltip: m['ranking.table.data.tooltips.rank']() },
        { id: 'name' },
        { id: 'elo', tooltip: m['ranking.table.data.tooltips.elo']() },
        { id: 'trust_range', tooltip: m['ranking.table.data.tooltips.trust_range']() },
        { id: 'n_match' },
        { id: 'consumption', tooltip: m['ranking.table.data.tooltips.consumption']() },
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
        // The rank column shows whichever the toggle asked for, so its header
        // and tooltip have to follow rather than always announce classes.
        ...(col.id === 'rank' && showRanks
          ? {
              label: m['ranking.table.data.cols.rank_number'](),
              tooltip: m['ranking.table.showRanks.help']()
            }
          : { label: m[`ranking.table.data.cols.${col.id}`]() }),
        orderable: true,
        colHeaderClass: raw ? 'bg-white! border-b-1 border-[--border-contrast-grey]' : ''
      }))
  )

  let orderingCol = $state(initialOrderCol)
  let orderingMethod = $state(initialOrderMethod)
  let search = $state('')

  const ROMAN = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII']
  const roman = (rankClass: string) => ROMAN[Number(rankClass) - 1] ?? rankClass

  // The shades come from the instance's own primary colour, so a rebranded
  // deployment gets a ranking ramp in its own palette rather than ours. Both
  // halves of the pair are needed: the label colour flips partway down the
  // ramp, which is what lets the ramp span its full range and stay readable.
  const classShade = (rankClass: string) =>
    `background: var(--brand-rank-${rankClass}); color: var(--brand-rank-${rankClass}-text)`

  $effect(() => {
    if (orderingCol === undefined) {
      orderingCol = initialOrderCol
      orderingMethod = initialOrderMethod
    }
  })

  const rows = $derived.by(() => {
    const models = data
      .filter((llm) => {
        if (filterProprietary) return llm.license.kind !== 'proprietary'
        return true
      })
      .sort((a, b) => sortIfDefined(a.data, b.data, 'elo'))

    if (models.length === 0) return []

    const highestConso = models.reduce((a, llm) => (llm.consumption > a ? llm.consumption : a), 0)

    // Every score bar shares one axis, so widths and offsets compare across
    // rows: the whole point is seeing which intervals overlap.
    const axisMin = models.reduce((a, llm) => Math.min(a, llm.data.score_p2_5), Infinity)
    const axisMax = models.reduce((a, llm) => Math.max(a, llm.data.score_p97_5), -Infinity)
    const axisSpan = Math.max(axisMax - axisMin, 1)
    const onAxis = (score: number) => ((score - axisMin) / axisSpan) * 100

    return models.map((model) => {
      const ciLeft = onAxis(model.data.score_p2_5)

      return {
        ...model,
        arch: (model.license.kind === 'proprietary' ? 'na' : model.arch) as Archs,
        release_date: model.release_date,
        ciLeft,
        // A hairline rather than nothing when the interval is vanishingly thin.
        ciWidth: Math.max(onAxis(model.data.score_p97_5) - ciLeft, 0.5),
        ciDot: onAxis(model.data.elo),
        consoRangeWidth: Math.ceil((model.consumption / highestConso) * 100)
      }
    })
  })

  const sortedRows = $derived.by(() => {
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
          case 'consumption': {
            const aProprietary = a.license.kind === 'proprietary'
            const bProprietary = b.license.kind === 'proprietary'
            if (aProprietary && bProprietary) return a.id.localeCompare(b.id)
            if (aProprietary) return orderingMethod === 'ascending' ? -1 : 1
            if (bProprietary) return orderingMethod === 'ascending' ? 1 : -1
            return b.consumption - a.consumption
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
          case 'organisation':
            return a.lab.name.localeCompare(b.lab.name)
          case 'arch':
            return a.arch.localeCompare(b.arch)
          case 'license':
            return a.license.kind.localeCompare(b.license.kind)
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
        {m['ranking.table.lastUpdate']({ date: lastUpdateDate! })}
      </p>

      {#if !raw}
        <div class="gap-2 flex items-center">
          <Toggle
            id="{id}-show-ranks"
            bind:value={showRanks}
            label={m['ranking.table.showRanks.label']()}
            hideCheckLabel
            class="mb-0! pr-13! text-[14px]! whitespace-nowrap"
          />
          <Tooltip id="{id}-show-ranks-help" size="sm">
            {m['ranking.table.showRanks.help']()}
          </Tooltip>
        </div>
      {/if}

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
      {#if showRanks || raw}
        <span class="font-medium">{model.data.rank}</span>
      {:else}
        <span
          class="px-2 py-1 text-xs font-bold inline-block min-w-[2.75rem] rounded-full text-center"
          style={classShade(model.data.rankClass)}
        >
          <span aria-hidden="true">{roman(model.data.rankClass)}</span>
          <!-- On its own a numeral reads as "I". Spell the column and the
               ranks it covers out for anyone who cannot see the chip. -->
          <span class="fr-sr-only"
            >{m['ranking.table.data.cols.rank']()}
            {roman(model.data.rankClass)}, {rankClassLabel(
              activeCommons.rankClasses[model.data.rankClass]
            )}</span
          >
        </span>
      {/if}
    {:else if col.id === 'name'}
      <div
        class="sm:max-w-none sm:overflow-visible max-w-[205px] overflow-hidden overflow-ellipsis"
      >
        <AILogo logo={model.lab.logo} alt={model.lab.name} class="me-1 inline-block align-middle" />
        <a
          href="#{model.human_id}"
          data-fr-opened="false"
          aria-controls="{id}-modal-model"
          class="text-black!"
          onclick={() => (selectedModel = model.id)}>{model.human_id}</a
        >
      </div>
    {:else if col.id === 'size'}
      <strong>{model.size_class}</strong> -
      {#if model.license.kind === 'proprietary'}
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
        <div class="gap-2 flex min-w-[160px] items-center">
          <div
            class="rounded-xs bg-light-info h-2 relative flex-1"
            title={m['ranking.table.data.tooltips.trust_range']()}
          >
            <div
              class="rounded-xs bg-info top-0 absolute h-full"
              style="left: {model.ciLeft}%; width: {model.ciWidth}%"
            ></div>
            <div
              class="bg-info h-2 w-2 ring-white absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2"
              style="left: {model.ciDot}%"
            ></div>
          </div>
          <span class="text-xs font-bold">{model.data.elo}</span>
        </div>
      {/if}
    {:else if col.id === 'trust_range'}
      -{model.data.trust_range![1]}/+{model.data.trust_range![0]}
    {:else if col.id === 'consumption'}
      {#if model.license.kind === 'proprietary'}
        <span class="text-xs text-[--grey-625-425]">{m['words.NA']()}</span>
      {:else}
        {model.consumption} mWh
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
      {model.lab.name}
    {/if}
  {/snippet}
</Table>

<ModelInfoModal commons={activeCommons} model={selectedModelData} modalId="{id}-modal-model" />
