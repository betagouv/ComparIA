<script lang="ts">
  import { resolve } from '$app/paths'
  import AILogo from '$components/AILogo.svelte'
  import { Table } from '$components/dsfr'
  import Link from '$components/dsfr/Link.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import type { OrderingMethod, TableCol } from '$lib/utils/data'
  import { sortRows, toRelativeTime, toSearchString } from '$lib/utils/data'

  import type { PageProps } from './$types'

  let { data }: PageProps = $props()
  const locale = getLocale()
  const baseRoute = '/admin/llms/labs' as const

  const labs = $derived(
    data.labs.map((lab) => ({
      ...lab,
      llms_count: data.llms.filter((llm) => llm.lab_id === lab.id!).length,
      updated_at: new Date(lab.updated_at!),
      created_at: new Date(lab.created_at!),
      id: lab.id!,
      search: toSearchString([lab.name, lab.id!, lab.origin_country])
    }))
  )
  type DataKey = keyof (typeof labs)[number]
  const cols = [
    { id: 'name', label: 'Name', orderable: true },
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
    sortRows(labs, cols, { col: orderingCol, method: orderingMethod, search })
  )
</script>

<Table
  bind:search
  bind:orderingMethod
  bind:orderingCol
  caption="Labs"
  hideCaption
  {cols}
  rows={sortedRows}
>
  {#snippet headerLeft()}
    <Link button icon="add-line" text={m['words.add']()} href={`${baseRoute}/create`} />
  {/snippet}

  {#snippet cell(lab, col)}
    {#if col.id === 'name'}
      <div class="gap-2 flex items-center">
        <AILogo logo={lab.logo} alt="" />
        <a href={resolve(`${baseRoute}/${lab.id}`)}>{lab[col.id]}</a>
      </div>
    {:else if col.id === 'created_at' || col.id === 'updated_at'}
      <span class="fr-text--sm text-[--text-mention-grey]">
        {toRelativeTime(lab[col.id], locale)}
      </span>
    {:else}
      {lab[col.id]}
    {/if}
  {/snippet}
</Table>
