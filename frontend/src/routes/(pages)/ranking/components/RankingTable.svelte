<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Link, Table } from '$components/dsfr'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import { getVotesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { getModelsWithDataContext, type Archs } from '$lib/models'
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
  const { lastUpdateDate, models: data } = getModelsWithDataContext()
  let selectedModel = $state<string>()
  const selectedModelData = $derived(data.find((m) => m.id === selectedModel))

  const cols = (
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
    const models = data
      .filter((m) => {
        if (filterProprietary) return m.license !== 'proprietary'
        return true
      })
      .sort((a, b) => sortIfDefined(a.data, b.data, 'elo'))

    if (models.length === 0) return []

    const highestConso = models.reduce((a, m) => (m.consumption > a ? m.consumption : a), 0)

    // Forest-plot shared x-axis bounds: full CI envelope across all displayed models.
    const axisMin = models.reduce(
      (a, m) => Math.min(a, m.data.score_p2_5),
      models[0].data.score_p2_5
    )
    const axisMax = models.reduce(
      (a, m) => Math.max(a, m.data.score_p97_5),
      models[0].data.score_p97_5
    )
    const axisSpan = Math.max(axisMax - axisMin, 1)

    // Tier assignment: greedy top-down on score CIs, anchored.
    // Each tier has a fixed anchor = the lower-CI of its topmost member,
    // set when the tier opens. A model joins iff its upper-CI overlaps
    // that anchor. The anchor does NOT drift — this prevents long chains
    // of "each model overlaps the previous" from collapsing everything
    // into Tier A when CIs are wide.
    const tiers: { letter: string; index: number }[] = []
    let tierLetterCode = 'A'.charCodeAt(0)
    let tierAnchorLowerCi = models[0].data.score_p2_5
    let tierIndex = 0
    for (const model of models) {
      if (model.data.score_p97_5 < tierAnchorLowerCi) {
        tierLetterCode += 1
        tierAnchorLowerCi = model.data.score_p2_5
        tierIndex = 0
      }
      tierIndex += 1
      tiers.push({ letter: String.fromCharCode(tierLetterCode), index: tierIndex })
    }

    // Compute tier-group metadata (size, position within group) so the
    // rank column can render one continuous tinted block per tier with
    // the letter centered vertically — like a CSS-faked rowspan.
    const tierMeta: {
      isFirstOfTier: boolean
      isLastOfTier: boolean
      isMiddleOfTier: boolean
    }[] = []
    let runStart = 0
    for (let i = 0; i <= tiers.length; i += 1) {
      const breaks = i === tiers.length || tiers[i].letter !== tiers[runStart].letter
      if (breaks) {
        const size = i - runStart
        const middle = runStart + Math.floor((size - 1) / 2)
        for (let j = runStart; j < i; j += 1) {
          tierMeta.push({
            isFirstOfTier: j === runStart,
            isLastOfTier: j === i - 1,
            isMiddleOfTier: j === middle
          })
        }
        runStart = i
      }
    }

    return models.map((model, i) => {
      const [month, year] = model.release_date.split('/')
      const ciLeft = ((model.data.score_p2_5 - axisMin) / axisSpan) * 100
      const ciRight = ((model.data.score_p97_5 - axisMin) / axisSpan) * 100
      const ciDot = ((model.data.elo - axisMin) / axisSpan) * 100

      return {
        ...model,
        arch: (model.license === 'proprietary' ? 'na' : model.arch) as Archs,
        release_date: new Date([month, '01', year].join('/')),
        tier: tiers[i].letter,
        tierIndex: tiers[i].index,
        tierLabel: `${tiers[i].letter}${tiers[i].index}`,
        isFirstOfTier: tierMeta[i].isFirstOfTier,
        isLastOfTier: tierMeta[i].isLastOfTier,
        isMiddleOfTier: tierMeta[i].isMiddleOfTier,
        ciLeft,
        ciWidth: Math.max(ciRight - ciLeft, 0.5),
        ciDot,
        consoRangeWidth: Math.ceil((model.consumption / highestConso) * 100)
      }
    })
  })

  // Stable color per tier letter. Cycles through DSFR-friendly hues so
  // adjacent tiers are visually distinct without screaming. Tiers beyond
  // the palette length wrap — in practice we expect 6–10 tiers.
  const TIER_COLORS: Record<string, { bg: string; text: string; bar: string; track: string }> = {
    A: { bg: '#e8f0ff', text: '#0050cc', bar: '#0050cc', track: '#cfe0ff' },
    B: { bg: '#e6f5ee', text: '#1f7a4d', bar: '#1f7a4d', track: '#c8e6d5' },
    C: { bg: '#f3ecff', text: '#6e3fcf', bar: '#6e3fcf', track: '#dccef0' },
    D: { bg: '#fff1e0', text: '#a85d00', bar: '#a85d00', track: '#f5d9b3' },
    E: { bg: '#ffe8e8', text: '#b13434', bar: '#b13434', track: '#f2c9c9' },
    F: { bg: '#eef0f3', text: '#4a5363', bar: '#4a5363', track: '#d2d6dd' }
  }
  const tierColor = (letter: string) => TIER_COLORS[letter] ?? TIER_COLORS.F

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
            const aProprietary = a.license === 'proprietary'
            const bProprietary = b.license === 'proprietary'
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
      {#if raw}
        <span class="font-medium">{model.tierLabel}</span>
      {:else}
        {@const c = tierColor(model.tier)}
        <div
          class="tier-block relative flex items-center justify-center"
          style="
            background: {c.bg};
            min-height: 2.75rem;
            margin-top: {model.isFirstOfTier ? '4px' : '-13px'};
            margin-bottom: {model.isLastOfTier ? '4px' : '-13px'};
            margin-left: -0.5rem;
            margin-right: -0.5rem;
            border-top-left-radius: {model.isFirstOfTier ? '6px' : 0};
            border-top-right-radius: {model.isFirstOfTier ? '6px' : 0};
            border-bottom-left-radius: {model.isLastOfTier ? '6px' : 0};
            border-bottom-right-radius: {model.isLastOfTier ? '6px' : 0};
          "
          title="Tier {model.tier} · rank {model.data.rank} (95% CI: {model.data
            .rank_p2_5}–{model.data.rank_p97_5})"
        >
          {#if model.isMiddleOfTier}
            <span
              class="text-xl font-bold tabular-nums"
              style="color: {c.text}; letter-spacing: 0.02em;">{model.tier}</span
            >
          {/if}
        </div>
      {/if}
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
        {@const c = tierColor(model.tier)}
        <div class="flex items-center gap-2" style="min-width: 180px;">
          <div
            class="rounded-sm relative h-2 flex-1"
            style="background: #f1f3f6;"
            title="95% CI: {model.data.score_p2_5}–{model.data.score_p97_5}"
          >
            <div
              class="rounded-sm absolute top-0 h-full"
              style="left: {model.ciLeft}%; width: {model.ciWidth}%; background: {c.track};"
            ></div>
            <div
              class="absolute top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
              style="left: {model.ciDot}%; width: 8px; height: 8px; background: {c.bar}; box-shadow: 0 0 0 2px white;"
            ></div>
          </div>
          <span class="text-xs font-bold tabular-nums" style="min-width: 2.5rem; text-align: right;"
            >{model.data.elo}</span
          >
        </div>
      {/if}
    {:else if col.id === 'trust_range'}
      -{model.data.trust_range![1]}/+{model.data.trust_range![0]}
    {:else if col.id === 'consumption'}
      {#if model.license === 'proprietary'}
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
      {model.organisation}
    {/if}
  {/snippet}
</Table>

<ModelInfoModal model={selectedModelData} modalId="{id}-modal-model" />
