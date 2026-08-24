<script lang="ts">
  import { resolve } from '$app/paths'
  import { Table } from '$components/dsfr'
  import Link from '$components/dsfr/Link.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import type { OrderingMethod, TableCol } from '$lib/utils/data'
  import { sortRows, toRelativeTime, toSearchString } from '$lib/utils/data'

  import type { PageProps } from './$types'

  let { data }: PageProps = $props()
  const locale = getLocale()
  const baseRoute = '/admin/outils' as const

  const tools = $derived(
    data.tools.map((tool) => ({
      ...tool,
      kind: tool.kind ?? 'builtin',
      enabled: tool.enabled ?? false,
      updated_at: new Date(tool.updated_at!),
      created_at: new Date(tool.created_at!),
      id: tool.id!,
      search: toSearchString([tool.label, tool.key, tool.description ?? ''])
    }))
  )
  type DataKey = keyof (typeof tools)[number]
  const cols = [
    { id: 'label', label: 'Label', orderable: true },
    { id: 'key', label: 'Key', orderable: true },
    { id: 'kind', label: 'Kind', orderable: true },
    { id: 'enabled', label: 'Enabled', orderable: true },
    { id: 'updated_at', label: 'Updated', kind: 'date', orderable: true }
  ] satisfies TableCol<DataKey>[]
  type ColKey = (typeof cols)[number]['id']

  let orderingCol = $state<ColKey>('label')
  let orderingMethod = $state<OrderingMethod>('descending')
  let search = $state('')

  const sortedRows = $derived(
    sortRows(tools, cols, { col: orderingCol, method: orderingMethod, search })
  )
</script>

<Table
  bind:search
  bind:orderingMethod
  bind:orderingCol
  caption="Tools"
  hideCaption
  {cols}
  rows={sortedRows}
>
  {#snippet headerLeft()}
    <Link button icon="add-line" text={m['words.add']()} href={`${baseRoute}/create`} />
  {/snippet}

  {#snippet cell(tool, col)}
    {#if col.id === 'label'}
      <a href={resolve(`${baseRoute}/${tool.id}`)}>{tool[col.id]}</a>
    {:else if col.id === 'enabled'}
      {tool.enabled ? m['words.activated']() : m['words.deactivated']()}
    {:else if col.id === 'updated_at'}
      <span class="fr-text--sm text-[--text-mention-grey]">
        {toRelativeTime(tool[col.id], locale)}
      </span>
    {:else}
      {tool[col.id]}
    {/if}
  {/snippet}
</Table>
