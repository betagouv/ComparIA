<script lang="ts">
  import { resolve } from '$app/paths'
  import { Badge, Link, Table } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { getLicenceBadge } from '$lib/models'
  import type { OrderingMethod, TableCol } from '$lib/utils/data'
  import { sortRows, toRelativeTime, toSearchString } from '$lib/utils/data'

  import type { PageProps } from './$types'

  let { data }: PageProps = $props()
  const locale = getLocale()
  const baseRoute = '/admin/llms/licenses' as const

  const licenses = $derived(
    data.licenses.map((lic) => ({
      ...lic,
      llms_count: data.llms.filter((llm) => llm.license_id === lic.id!).length,
      updated_at: new Date(lic.updated_at!),
      created_at: new Date(lic.created_at!),
      id: lic.id!,
      search: toSearchString([lic.name, lic.id!, lic.kind])
    }))
  )
  type DataKey = keyof (typeof licenses)[number]
  const cols = [
    { id: 'name', label: 'Name', orderable: true },
    { id: 'kind', label: 'Kind', orderable: true },
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
    sortRows(licenses, cols, { col: orderingCol, method: orderingMethod, search })
  )
</script>

<Table
  bind:search
  bind:orderingMethod
  bind:orderingCol
  caption="Licenses"
  hideCaption
  {cols}
  rows={sortedRows}
>
  {#snippet headerLeft()}
    <Link button icon="add-line" text={m['words.add']()} href={`${baseRoute}/create`} />
  {/snippet}

  {#snippet cell(lic, col)}
    {#if col.id === 'name'}
      <a href={resolve(`${baseRoute}/${lic.id}`)}>{lic[col.id]}</a>
    {:else if col.id === 'kind'}
      <Badge {...getLicenceBadge(lic.kind)} size="xs" tooltip={undefined} />
    {:else if col.id === 'created_at' || col.id === 'updated_at'}
      <span class="fr-text--sm text-[--text-mention-grey]">
        {toRelativeTime(lic[col.id], locale)}
      </span>
    {:else}
      {lic[col.id]}
    {/if}
  {/snippet}
</Table>
