<script lang="ts">
  import { Link, Table, Toggle } from '$components/dsfr'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import {
    APINegativeReactions,
    APIPositiveReactions,
    type APIReactionPref
  } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { getModelsWithDataContext } from '$lib/models'
  import { sortIfDefined } from '$lib/utils/data'

  type ColKind =
    | 'name'
    | 'positive_prefs_ratio'
    | 'total_positive_prefs'
    | 'total_negative_prefs'
    | APIReactionPref

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

  const { lastUpdateDate, models: data } = getModelsWithDataContext()
  let selectedModel = $state<string>()
  const selectedModelData = $derived(data.find((m) => m.id === selectedModel))

  const cols = (
    [
      { id: 'name', orderable: true },
      {
        id: 'positive_prefs_ratio',
        tooltip: m['ranking.preferences.table.tooltips.positive_prefs_ratio'](),
        orderable: true
      },
      { id: 'total_positive_prefs' },
      { id: 'total_negative_prefs' },
      ...APIPositiveReactions.map((reaction, i) => ({
        id: reaction,
        colHeaderClass: 'bg-(--green-emeraude-975-75)!',
        orderable: true
      })),
      ...APINegativeReactions.map((reaction, i) => ({
        id: reaction,
        colHeaderClass: 'bg-(--warning-950-100)!',
        orderable: true
      }))
    ] as const
  ).map((col) => ({
    ...col,
    label: m[`ranking.preferences.table.cols.${col.id}`]()
  }))

  let orderingCol = $state(initialOrderCol)
  let orderingMethod = $state(initialOrderMethod)
  let search = $state('')
  let asPercentage = $state(false)

  $effect(() => {
    if (orderingCol === undefined) {
      orderingCol = initialOrderCol
      orderingMethod = initialOrderMethod
    }
  })

  const rows = $derived.by(() => {
    return data.map((model) => ({
      id: model.id,
      simple_name: model.simple_name,
      icon_path: model.icon_path,
      organisation: model.organisation,
      ...model.prefs,
      total_positive_prefs: APIPositiveReactions.reduce((acc, v) => acc + model.prefs[v], 0),
      total_negative_prefs: APINegativeReactions.reduce((acc, v) => acc + model.prefs[v], 0),
      search: (['id', 'simple_name', 'organisation'] as const)
        .map((key) => model[key].toLowerCase())
        .join(' ')
    }))
  })

  const sortedRows = $derived.by(() => {
    const _search = search.toLowerCase()

    return rows
      .filter((m) => (!_search ? true : m.search.includes(_search)))
      .sort((ma, mb) => {
        const [a, b] = orderingMethod === 'ascending' ? [mb, ma] : [ma, mb]
        return sortIfDefined(a, b, orderingCol)
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
  searchLabel={m['ranking.table.search']()}
  caption={m['ranking.title']()}
  hideCaption
>
  {#snippet headerLeft()}
    <div class="fr-table__detail mb-0! flex gap-5">
      <p class="mb-0! text-[14px]!">
        {m['ranking.table.lastUpdate']({ date: lastUpdateDate })}
      </p>

      <Link
        href="#"
        download="true"
        text={m['actions.downloadData']()}
        icon="download-line"
        iconPos="right"
        class="text-[14px]! text-grey!"
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
      class="text-[14px]! me-14"
    />
  {/snippet}

  {#snippet cell(model, col)}
    {#if col.id === 'name'}
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
    {:else if col.id === 'total_positive_prefs' || col.id === 'total_negative_prefs'}
      <strong>{model[col.id]}</strong>
    {:else if col.id === 'positive_prefs_ratio'}
      {@const size = Math.round(model[col.id] * 100)}
      <div class="flex h-[25px] w-full rounded-sm border border-[#cecece] text-[12px] font-bold">
        <div
          class="w-(--width) bg-(--green-emeraude-975-75) text-(--green-emeraude-sun-425-moon-753) rounded-s-sm ps-1"
          style="width: {size}%"
        >
          {size}%
        </div>
        <div class="bg-(--warning-950-100) text-(--warning-425-625) grow rounded-e-sm ps-1">
          {Math.round((1 - model[col.id]) * 100)}%
        </div>
      </div>
    {:else if asPercentage}
      {Math.round((model[col.id] / model.total_prefs) * 100)}%
    {:else}
      {model[col.id]}
    {/if}
  {/snippet}
</Table>

<ModelInfoModal model={selectedModelData} modalId="{id}-modal-model" />
