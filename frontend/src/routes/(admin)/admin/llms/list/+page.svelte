<script lang="ts">
  import { Badge, Icon, Table } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { sortIfDefined } from '$lib/utils/data'

  import type { PageProps } from './$types'

  let { data }: PageProps = $props()
  const locale = getLocale()

  const llms = $derived(
    data.llms.map((llm) => ({
      ...llm,
      id: llm.id!,
      votes: llm.data?.n_match,
      search: [llm.human_id, llm.name, llm.id].join(' '),
      release_date: new Date(llm.release_date),
      updated_at: new Date(llm.updated_at),
      created_at: new Date(llm.created_at)
    }))
  )
  const cols = [
    { id: 'human_id' as const, label: 'Human ID', orderable: true },
    { id: 'status' as const, label: 'Status', orderable: true },
    { id: 'rate_limited' as const, label: 'Rate limited', orderable: true },
    { id: 'release_date' as const, label: 'Release date', orderable: true },
    { id: 'created_at' as const, label: 'Added', orderable: true },
    { id: 'updated_at' as const, label: 'Updated', orderable: true },
    { id: 'id' as const, label: 'UUID' },
    { id: 'votes' as const, label: 'Vote count', orderable: true }
  ]

  let orderingCol = $state<(typeof cols)[number]['id']>('human_id')
  let orderingMethod = $state<'ascending' | 'descending'>('descending')
  let search = $state('')

  $effect(() => {
    if (orderingCol === undefined) {
      orderingCol = 'human_id'
      orderingMethod = 'descending'
    }
  })

  function relativeTime(iso: Date): string {
    const diff = Date.now() - iso.getTime()
    const days = Math.floor(diff / 86400000)
    if (days === 0) return 'today'
    if (days === 1) return '1 day ago'
    if (days < 30) return `${days} days ago`
    const months = Math.floor(days / 30)
    if (months === 1) return '1 month ago'
    return `${months} months ago`
  }

  const sortedRows = $derived.by(() => {
    const _search = search.toLowerCase()

    return llms
      .filter((llm) => (!_search ? true : llm.search.includes(_search)))
      .sort((ma, mb) => {
        const [a, b] = orderingMethod === 'ascending' ? [mb, ma] : [ma, mb]

        switch (orderingCol) {
          case 'votes':
            return sortIfDefined(a, b, orderingCol)
          case 'release_date':
          case 'updated_at':
          case 'created_at':
            return b[orderingCol] - a[orderingCol]
          case 'rate_limited':
            return a.rate_limited && b.rate_limited ? 0 : a.rate_limited ? 1 : -1
          default:
            return a[orderingCol].localeCompare(b[orderingCol])
        }
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
      {llm.release_date.toLocaleString(locale, { year: 'numeric', month: 'numeric' })}
    {:else if col.id === 'created_at' || col.id === 'updated_at'}
      <span class="fr-text--sm text-[--text-mention-grey]">{relativeTime(llm[col.id])}</span>
    {:else}
      {llm[col.id]}
    {/if}
  {/snippet}
</Table>
