<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Link, Table } from '$components/dsfr'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { isMaybeArch, type BotModel, type Commons, type PersonalRow } from '$lib/models'
  import { toShortDate } from '$lib/utils/data'

  type ColKind =
    | 'rank'
    | 'name'
    | 'score'
    | 'battles'
    | 'record'
    | 'general_rank'
    | 'size'
    | 'arch'
    | 'release'
    | 'organisation'
    | 'license'

  let {
    id,
    rows: rows_,
    commons,
    votesCount,
    onDownloadData
  }: {
    // Scored, ordered and numbered by the server: nothing here re-ranks them.
    rows: PersonalRow[]
    id: string
    commons: Commons
    votesCount: number
    onDownloadData: () => void
  } = $props()

  const locale = getLocale()
  const rows = $derived(
    rows_.map((row) => ({
      ...row,
      winsSize: Math.round((row.wins / row.battles) * 100),
      lossesSize: Math.round((row.losses / row.battles) * 100)
    }))
  )

  // Proprietary models publish no architecture, and neither do the ones we
  // only have a guess for.
  const archKey = (model: BotModel) =>
    model.license.kind === 'proprietary' || isMaybeArch(model.arch) ? 'na' : model.arch

  const scoreFormatter = new Intl.NumberFormat(locale, {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3
  })
  const votesLabel = $derived(new Intl.NumberFormat(locale).format(votesCount))

  let selectedModel = $state<string>()
  const selectedModelData = $derived(
    rows.find((row) => row.id === selectedModel)?.model ?? undefined
  )

  const cols = $derived(
    (
      [
        {
          id: 'rank',
          label: m['ranking.table.data.cols.rank_number'](),
          tooltip: m['ranking.personal.tooltips.rank']()
        },
        { id: 'name', label: m['ranking.table.data.cols.name']() },
        {
          id: 'score',
          label: m['ranking.personal.cols.score'](),
          tooltip: m['ranking.personal.tooltips.score'](),
          hidden: true
        },
        {
          id: 'battles',
          label: m['ranking.personal.cols.battles'](),
          tooltip: m['ranking.personal.tooltips.battles']()
        },
        {
          id: 'record',
          label: m['ranking.personal.cols.record'](),
          tooltip: m['ranking.personal.tooltips.record']()
        },
        {
          id: 'general_rank',
          label: m['ranking.personal.cols.general_rank'](),
          tooltip: m['ranking.personal.tooltips.general_rank']()
        },
        {
          id: 'size',
          label: m['ranking.table.data.cols.size'](),
          tooltip: m['ranking.table.data.tooltips.size']()
        },
        {
          id: 'arch',
          label: m['ranking.table.data.cols.arch'](),
          tooltip: m['ranking.table.data.tooltips.arch']()
        },
        { id: 'release', label: m['ranking.table.data.cols.release']() },
        { id: 'organisation', label: m['ranking.table.data.cols.organisation']() },
        { id: 'license', label: m['ranking.table.data.cols.license']() }
      ] as const
    ).map((col) => ({ ...col, orderable: true }))
  )

  let orderingCol = $state<ColKind | undefined>('score')
  let orderingMethod = $state<'ascending' | 'descending'>('descending')
  let search = $state('')

  $effect(() => {
    if (orderingCol === undefined) {
      orderingCol = 'score'
      orderingMethod = 'descending'
    }
  })

  const sortedRows = $derived.by(() => {
    const _search = search.toLowerCase()

    return rows
      .filter((row) => (!_search ? true : row.search.toLowerCase().includes(_search)))
      .sort((ra, rb) => {
        const [a, b] = orderingMethod === 'ascending' ? [rb, ra] : [ra, rb]

        switch (orderingCol) {
          case 'name':
            return (a.model?.human_id ?? a.name).localeCompare(b.model?.human_id ?? b.name)
          case 'score':
            return b.score - a.score
          case 'battles':
            return b.battles - a.battles
          case 'record':
            return b.wins - a.wins
          case 'general_rank': {
            // A model the general ranking does not hold sits at the end either
            // way round: it has no position to compare. Decided on the rows as
            // given rather than the swapped pair, so reversing the column does
            // not carry the missing ones to the top with it.
            const aMissing = ra.generalRank === null
            const bMissing = rb.generalRank === null
            if (aMissing || bMissing) return aMissing === bMissing ? 0 : aMissing ? 1 : -1
            return a.generalRank! - b.generalRank!
          }
          case 'size':
            return (b.model?.params ?? 0) - (a.model?.params ?? 0)
          case 'arch':
            return (a.model?.arch ?? '').localeCompare(b.model?.arch ?? '')
          case 'release':
            return Number(b.model?.release_date ?? 0) - Number(a.model?.release_date ?? 0)
          case 'organisation':
            return (a.model?.lab.name ?? '').localeCompare(b.model?.lab.name ?? '')
          case 'license':
            return (a.model?.license.kind ?? '').localeCompare(b.model?.license.kind ?? '')
          default:
            return a.rank - b.rank
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
  caption={m['ranking.personal.title']()}
  hideCaption
>
  {#snippet headerLeft()}
    <div class="gap-5 flex">
      <div class="cg-border rounded-sm! bg-white px-4 py-2">
        <strong>{m['ranking.personal.totalModels']()}</strong>
        <span class="text-grey">{rows.length}</span>
      </div>

      <div class="cg-border rounded-sm! bg-white px-4 py-2">
        <strong>{m['ranking.personal.totalVotes']()}</strong>
        <span class="text-grey">{votesLabel}</span>
      </div>
    </div>

    <div class="fr-table__detail mb-0!">
      <Link
        href="#"
        download="true"
        text={m['actions.downloadData']()}
        icon="download-line"
        iconPos="right"
        class="bg-none! text-[14px]! no-underline!"
        onclick={() => onDownloadData()}
      />
    </div>
  {/snippet}

  {#snippet cell(row, col)}
    {#if col.id === 'rank'}
      <span class="font-medium">{row.rank}</span>
    {:else if col.id === 'name'}
      <div
        class="sm:max-w-none sm:overflow-visible max-w-[205px] overflow-hidden overflow-ellipsis"
      >
        {#if row.model}
          <AILogo
            logo={row.model.lab.logo}
            customLogoId={row.model.lab.has_custom_logo ? row.model.lab.id : undefined}
            customLogoVersion={row.model.lab.logo_version}
            alt={row.model.lab.name}
            class="me-1 inline-block align-middle"
          />
          <a
            href="#{row.model.human_id}"
            data-fr-opened="false"
            aria-controls="{id}-modal-model"
            class="text-black!"
            onclick={() => (selectedModel = row.id)}>{row.model.human_id}</a
          >
        {:else}
          <!-- Voted on, then dropped from the catalogue, so there is no model
               card to open. Still listed: it is part of the user's record. -->
          <span>{row.name}</span>
        {/if}
      </div>
    {:else if col.id === 'score'}
      <span class="font-bold">{scoreFormatter.format(row.score)}</span>
    {:else if col.id === 'battles'}
      {row.battles}
    {:else if col.id === 'record'}
      {row.wins}-{row.ties}-{row.losses}
      <div
        aria-hidden="true"
        class="h-2 flex w-full overflow-hidden rounded-full bg-[--grey-925-125]"
      >
        <div class="w-[--width] bg-[--green-emeraude-850-200]" style="width: {row.winsSize}%"></div>
        <div class="bg-red ms-auto w-[--width]" style="width: {row.lossesSize}%"></div>
      </div>
    {:else if col.id === 'general_rank'}
      <!-- Blank, not zero: the model can be missing from the general ranking
           and still be in the user's own. -->
      {#if row.generalRank !== null}{row.generalRank}{/if}
    {:else if col.id === 'size'}
      {#if row.model}
        <strong>{row.model.size_class}</strong> -
        {#if row.model.license.kind === 'proprietary'}
          <span class="text-xs">{m['ranking.table.data.estimation']()}</span>
        {:else}
          {m['ranking.table.data.billions']({ count: row.model.params })}
        {/if}
      {:else}
        <span class="text-xs text-[--grey-625-425]">{m['words.NA']()}</span>
      {/if}
    {:else if col.id === 'arch'}
      {#if row.model}
        {m[`generated.archs.${archKey(row.model)}.name`]()}
      {:else}
        <span class="text-xs text-[--grey-625-425]">{m['words.NA']()}</span>
      {/if}
    {:else}
      {#if row.model}
        {#if col.id === 'release'}
          {toShortDate(row.model.release_date, locale, '2-digit')}
        {:else if col.id === 'organisation'}
          {row.model.lab.name}
        {:else if col.id === 'license'}
          <Badge {...row.model.badges.license} size="xs" noTooltip />
        {/if}
      {:else}
        <span class="text-xs text-[--grey-625-425]">{m['words.NA']()}</span>
      {/if}
    {/if}
  {/snippet}
</Table>

<ModelInfoModal {commons} model={selectedModelData} modalId="{id}-modal-model" />
