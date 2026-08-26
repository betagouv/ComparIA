<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Link, Table, Toggle } from '$components/dsfr'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import { m } from '$lib/i18n/messages'
  import { getModelsWithDataContext } from '$lib/models'
  import { sortIfDefined } from '$lib/utils/data'
  import { getVoteTagsContext, voteTagColLabel, voteTagsBySign, type VoteTag } from '$lib/voteTags'

  // 'name', 'positive_prefs_ratio', the two totals, or a vote tag key.
  type ColKind = string

  let {
    id,
    initialOrderCol = 'positive_prefs_ratio',
    initialOrderMethod = 'descending',
    onDownloadData
  }: {
    id: string
    initialOrderCol?: ColKind
    initialOrderMethod?: 'ascending' | 'descending'
    onDownloadData: () => void
  } = $props()

  const { lastUpdateDate, models: data, commons } = getModelsWithDataContext()
  let selectedModel = $state<string>()
  const selectedModelData = $derived(data.find((m) => m.id === selectedModel))

  const tags = getVoteTagsContext()
  const positiveTags = $derived(voteTagsBySign(tags, 'positive'))
  const negativeTags = $derived(voteTagsBySign(tags, 'negative'))
  // A model has no positive share to report when the instance turned off a
  // whole side of the taxonomy, so the column goes with it.
  const hasRatio = $derived(positiveTags.length > 0 && negativeTags.length > 0)

  const cols = $derived([
    { id: 'name', label: m['ranking.preferences.table.cols.name'](), orderable: true },
    ...(hasRatio
      ? [
          {
            id: 'positive_prefs_ratio',
            label: m['ranking.preferences.table.cols.positive_prefs_ratio'](),
            tooltip: m['ranking.preferences.table.tooltips.positive_prefs_ratio'](),
            orderable: true
          }
        ]
      : []),
    {
      id: 'total_positive_prefs',
      label: m['ranking.preferences.table.cols.total_positive_prefs']()
    },
    {
      id: 'total_negative_prefs',
      label: m['ranking.preferences.table.cols.total_negative_prefs']()
    },
    ...positiveTags.map((tag) => ({
      id: tag.key,
      label: voteTagColLabel(tag),
      colHeaderClass: 'bg-[--green-emeraude-975-75]!',
      orderable: true
    })),
    ...negativeTags.map((tag) => ({
      id: tag.key,
      label: voteTagColLabel(tag),
      colHeaderClass: 'bg-[--warning-950-100]!',
      orderable: true
    }))
  ])

  // Falls back to a total when the instance has no positive share to sort on.
  const defaultOrderCol = $derived(
    hasRatio
      ? initialOrderCol
      : positiveTags.length
        ? 'total_positive_prefs'
        : 'total_negative_prefs'
  )

  let orderingCol = $state<ColKind | undefined>(undefined)
  let orderingMethod = $state(initialOrderMethod)
  let search = $state('')
  let asPercentage = $state(false)

  $effect(() => {
    if (orderingCol === undefined) {
      orderingCol = defaultOrderCol
      orderingMethod = initialOrderMethod
    }
  })

  function sumCounts(counts: Record<string, number>, forTags: VoteTag[]) {
    return forTags.reduce((acc, tag) => acc + (counts[tag.key] ?? 0), 0)
  }

  const rows = $derived.by(() => {
    return data.map((model) => ({
      id: model.id,
      human_id: model.human_id,
      simple_name: model.name,
      logo: model.lab.logo,
      customLogoId: model.lab.has_custom_logo ? model.lab.id : undefined,
      organisation: model.lab.name,
      ...model.prefs,
      ...model.prefs.counts,
      total_positive_prefs: sumCounts(model.prefs.counts, positiveTags),
      total_negative_prefs: sumCounts(model.prefs.counts, negativeTags),
      search: model.search
    }))
  })

  const sortedRows = $derived.by(() => {
    const _search = search.toLowerCase()

    return rows
      .filter((m) => (!_search ? true : m.search.includes(_search)))
      .sort((ma, mb) => {
        const [a, b] = orderingMethod === 'ascending' ? [mb, ma] : [ma, mb]
        return sortIfDefined(a, b, orderingCol ?? defaultOrderCol)
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
  caption={m['ranking.preferences.title']()}
  hideCaption
>
  {#snippet headerLeft()}
    <div class="fr-table__detail mb-0! gap-5 flex">
      <p class="mb-0! text-[14px]!">
        {m['ranking.table.lastUpdate']({ date: lastUpdateDate! })}
      </p>

      <Link
        href="#"
        download="true"
        text={m['actions.downloadData']()}
        icon="download-line"
        iconPos="right"
        class="text-grey! bg-none! text-[14px]! no-underline!"
        onclick={() => onDownloadData()}
      />
    </div>
  {/snippet}

  {#snippet headerRight()}
    <Toggle
      id="data-as-percentage"
      bind:value={asPercentage}
      label={m['ranking.preferences.table.percentLabel']()}
      hideCheckLabel
      variant="primary"
      class="me-14 text-[14px]!"
    />
  {/snippet}

  {#snippet cell(model, col)}
    {#if col.id === 'name'}
      <AILogo
        logo={model.logo}
        customLogoId={model.customLogoId}
        alt={model.organisation}
        class="me-1 inline-block align-middle"
      />
      <a
        href="#{model.id}"
        data-fr-opened="false"
        aria-controls="{id}-modal-model"
        class="text-black!"
        onclick={() => (selectedModel = model.id)}>{model.human_id}</a
      >
    {:else if col.id === 'total_positive_prefs' || col.id === 'total_negative_prefs'}
      <strong>{model[col.id]}</strong>
    {:else if col.id === 'positive_prefs_ratio'}
      {#if model.positive_prefs_ratio === null}
        -
      {:else}
        {@const size = Math.round(model.positive_prefs_ratio * 100)}
        <div class="rounded-sm font-bold flex h-[25px] w-full border border-[#cecece] text-[12px]">
          <div
            class="rounded-s-sm ps-1 w-[--width] bg-[--green-emeraude-975-75] text-[--green-emeraude-sun-425-moon-753]"
            style="width: {size}%"
          >
            {size}%
          </div>
          <div class="rounded-e-sm ps-1 grow bg-[--warning-950-100] text-[--warning-425-625]">
            {100 - size}%
          </div>
        </div>
      {/if}
    {:else if asPercentage}
      {Math.round(((model.counts[col.id] ?? 0) / model.total_prefs) * 100)}%
    {:else}
      {model.counts[col.id] ?? 0}
    {/if}
  {/snippet}
</Table>

<ModelInfoModal {commons} model={selectedModelData} modalId="{id}-modal-model" />
