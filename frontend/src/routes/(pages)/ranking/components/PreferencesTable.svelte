<script lang="ts">
  import { Badge, Link, Search, Table } from '$components/dsfr'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import { negativeReactions, positiveReactions, type ReactionPref } from '$lib/chatService.svelte'
  import { getVotesContext } from '$lib/global.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import type { BotModel } from '$lib/models'
  import { sortIfDefined } from '$lib/utils/data'

  type ColKind = 'name' | 'total_prefs' | 'positive_prefs_ratio' | ReactionPref

  let {
    id,
    data,
    initialOrderCol = 'positive_prefs_ratio',
    initialOrderMethod = 'descending',
    onDownloadData
  }: {
    id: string
    data: BotModel[]
    initialOrderCol?: ColKind
    initialOrderMethod?: 'ascending' | 'descending'
    onDownloadData: () => void
  } = $props()

  const NumberFormater = new Intl.NumberFormat(getLocale(), { maximumSignificantDigits: 3 })

  // FIXME retrieve info from backend
  let lastUpdateDate = new Date()
  let selectedModel = $state<string>()
  const selectedModelData = $derived(data.find((m) => m.id === selectedModel))

  const cols = (
    [
      { id: 'name', label: m['ranking.table.data.cols.name']() },
      { id: 'total_prefs', label: m['ranking.preferences.table.cols.total_prefs']() },
      {
        id: 'positive_prefs_ratio',
        label: m['ranking.preferences.table.cols.positive_prefs_ratio'](),
        tooltip: 'FIXME'
      },
      ...positiveReactions.map((reaction) => ({
        id: reaction,
        label: m[`vote.choices.positive.${reaction}`]()
      })),
      ...negativeReactions.map((reaction) => ({
        id: reaction,
        label: m[`vote.choices.negative.${reaction}`]()
      }))
    ] as const
  ).map((col) => ({
    ...col,
    orderable: true
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

  function getRandomInt(min: number, max: number) {
    min = Math.ceil(min)
    max = Math.floor(max)
    return Math.floor(Math.random() * (max - min + 1)) + min
  }

  const rows = $derived.by(() => {
    const models = data.sort((a, b) => sortIfDefined(a, b, 'elo'))

    return models.map((model) => {
      // FIXME fake data
      const positiveCount = positiveReactions.map(() => getRandomInt(50, 150))
      const negativeCount = negativeReactions.map(() => getRandomInt(20, 50))
      const p = positiveCount.reduce((acc, n) => acc + n, 0)
      const n = negativeCount.reduce((acc, n) => acc + n, 0)
      const t = p + n
      return {
        ...model,
        total_prefs: t,
        positive_prefs_ratio: p / t,
        ...Object.fromEntries(positiveReactions.map((r, i) => [r, positiveCount[i] / t])),
        ...Object.fromEntries(negativeReactions.map((r, i) => [r, negativeCount[i] / t])),
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
      .sort((ma, mb) => {
        const [a, b] = orderingMethod === 'ascending' ? [mb, ma] : [ma, mb]
        return sortIfDefined(a, b, orderingCol)
      })
  })
</script>

FIXME FAUSSE DATA
<Table
  {id}
  {cols}
  rows={sortedRows}
  bind:orderingCol
  bind:orderingMethod
  caption={m['ranking.title']()}
  hideCaption
>
  {#snippet header()}
    <div class="flex flex-wrap items-center gap-5">
      <div class="fr-table__detail mb-0! flex gap-5">
        <p class="mb-0! text-[14px]!">
          {m['ranking.table.lastUpdate']({ date: lastUpdateDate.toLocaleDateString() })}
        </p>

        <!-- FIXME 404 -->
        <Link
          native={false}
          href="#"
          download="true"
          text={m['actions.downloadData']()}
          icon="download-line"
          iconPos="right"
          class="text-[14px]!"
          onclick={() => onDownloadData()}
        />
      </div>
    </div>

    <Search id="model-search" bind:value={search} label={m['ranking.table.search']()} />
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
    {:else if col.id === 'total_prefs'}
      <strong>{model.total_prefs}</strong>
    {:else if col.id === 'positive_prefs_ratio'}
      {@const size = Math.ceil(model[col.id] * 100)}
      <div class="flex h-[25px] w-full rounded-sm border border-[#CACACA] text-[12px] font-bold">
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
    {:else}
      {Math.round(model[col.id] * 100)}%
    {/if}
  {/snippet}
</Table>

<ModelInfoModal model={selectedModelData} modalId="{id}-modal-model" />
