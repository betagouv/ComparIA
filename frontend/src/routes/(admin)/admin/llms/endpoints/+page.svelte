<script lang="ts">
  import { Icon, Table } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import type { OrderingMethod, TableCol } from '$lib/utils/data'
  import { sortRows, toRelativeTime, toSearchString } from '$lib/utils/data'
  import type { PageProps } from './$types'

  let { data }: PageProps = $props()
  const locale = getLocale()

  const endpoints = $derived(
    data.endpoints.map((endpoint) => ({
      ...endpoint,
      configured: !!endpoint.api_key,
      llms_count: data.llms.filter((llm) => llm.endpoint_id === endpoint.id!).length,
      updated_at: new Date(endpoint.updated_at!),
      created_at: new Date(endpoint.created_at!),
      id: endpoint.id!,
      search: toSearchString([endpoint.name, endpoint.id!, endpoint.api_type])
    }))
  )
  type DataKey = keyof (typeof endpoints)[number]
  const cols = [
    { id: 'name', label: 'Name', orderable: true },
    { id: 'configured', label: 'Configured', kind: 'boolean', orderable: true },
    { id: 'api_type', label: 'Kind', orderable: true },
    { id: 'llms_count', label: 'LLMs', kind: 'number', orderable: true },
    { id: 'created_at', label: 'Added', kind: 'date', orderable: true },
    { id: 'updated_at', label: 'Updated', kind: 'date', orderable: true },
    { id: 'id', label: 'UUID' }
  ] satisfies TableCol<DataKey>[]
  type ColKey = (typeof cols)[number]['id']

  let orderingCol = $state<ColKey>('name')
  let orderingMethod = $state<OrderingMethod>('descending')
  let search = $state('')

  $effect(() => {
    if (orderingCol === undefined) {
      orderingCol = 'name'
      orderingMethod = 'descending'
    }
  })

  const sortedRows = $derived(
    sortRows(endpoints, cols, { col: orderingCol, method: orderingMethod, search })
  )
</script>

<Table
  bind:search
  bind:orderingMethod
  bind:orderingCol
  caption="Endpoints"
  hideCaption
  {cols}
  rows={sortedRows}
>
  {#snippet cell(endpoint, col)}
    {#if col.id === 'created_at' || col.id === 'updated_at'}
      <span class="fr-text--sm text-[--text-mention-grey]">
        {toRelativeTime(endpoint[col.id], locale)}
      </span>
    {:else if col.id === 'configured'}
      {#if endpoint.configured}
        <Icon icon="i-ri-check-line" class="text-success" aria-label={m['words.yes']()} />
      {:else}
        <Icon icon="i-ri-close-line" class="text-error" aria-label={m['words.no']()} />
      {/if}
    {:else}
      {endpoint[col.id]}
    {/if}
  {/snippet}
</Table>
