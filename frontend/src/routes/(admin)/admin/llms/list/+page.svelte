<script lang="ts">
  import { Badge, Icon, Table } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import {
    sortRows,
    toRelativeTime,
    toSearchString,
    toShortDate,
    type TableCol
  } from '$lib/utils/data'

  import type { PageProps } from './$types'

  let { data }: PageProps = $props()
  const locale = getLocale()

  const llms = $derived(
    data.llms.map((llm) => ({
      ...llm,
      votes: data.data.models.find((other) => other.id === llm.id)?.data?.n_match,
      release_date: new Date(llm.release_date),
      updated_at: new Date(llm.updated_at),
      created_at: new Date(llm.created_at),
      id: llm.id!,
      search: toSearchString([llm.human_id, llm.name, llm.id!])
    }))
  )
  type DataKey = keyof Omit<(typeof llms)[number], 'links'>

  const cols = [
    { id: 'human_id', label: 'Human ID', orderable: true },
    { id: 'status', label: 'Status', orderable: true },
    { id: 'rate_limited', label: 'Rate limited', kind: 'boolean', orderable: true },
    { id: 'release_date', label: 'Release date', kind: 'date', orderable: true },
    { id: 'created_at', label: 'Added', kind: 'date', orderable: true },
    { id: 'updated_at', label: 'Updated', kind: 'date', orderable: true },
    { id: 'id', label: 'UUID' },
    { id: 'votes', label: 'Vote count', kind: 'number', orderable: true }
  ] satisfies TableCol<DataKey>[]
  type ColKey = (typeof cols)[number]['id']

  let orderingCol = $state<ColKey>('human_id')
  let orderingMethod = $state<'ascending' | 'descending'>('descending')
  let search = $state('')

  $effect(() => {
    if (orderingCol === undefined) {
      orderingCol = 'human_id'
      orderingMethod = 'descending'
    }
  })

  const sortedRows = $derived.by(() => {
    const _search = search.toLowerCase()

    return sortRows(llms, cols, {
      col: orderingCol,
      method: orderingMethod,
      search: search.toLowerCase()
    })
  })
</script>

<Table
  bind:search
  bind:orderingMethod
  bind:orderingCol
  caption="LLMs"
  hideCaption
  {cols}
  rows={sortedRows}
>
  {#snippet cell(llm, col)}
    {#if col.id === 'human_id'}
      {llm[col.id]}
    {:else if col.id === 'status'}
      {@const status = llm[col.id]}
      <Badge
        size="sm"
        text={status}
        variant={status === 'enabled' ? 'green' : status === 'disabled' ? 'red' : ''}
      />
    {:else if col.id === 'rate_limited'}
      {#if llm.rate_limited}
        <Icon icon="i-ri-check-line" class="text-success" aria-label={m['words.yes']()} />
      {:else}
        <span class="sr-only">{m['words.no']()}</span>
      {/if}
    {:else if col.id === 'release_date'}
      {toShortDate(llm.release_date, locale)}
    {:else if col.id === 'created_at' || col.id === 'updated_at'}
      <span class="fr-text--sm text-[--text-mention-grey]">
        {toRelativeTime(llm[col.id], locale)}
      </span>
    {:else}
      {llm[col.id]}
    {/if}
  {/snippet}
</Table>
