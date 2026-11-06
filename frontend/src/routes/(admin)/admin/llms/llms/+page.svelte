<script lang="ts">
  import { resolve } from '$app/paths'
  import { Badge, Button, Icon, Link, Table } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import type { OrderingMethod, TableCol } from '$lib/utils/data'
  import { sortRows, toRelativeTime, toSearchString, toShortDate } from '$lib/utils/data'

  import type { PageProps } from './$types'
  import { useLLMHealth } from './llmHealth.svelte'
  import type { LLMHealthResult } from './types'

  let { data }: PageProps = $props()
  const locale = getLocale()
  const baseRoute = '/admin/llms/llms' as const
  const health = useLLMHealth()

  const healthLabels: Record<NonNullable<LLMHealthResult['error']>, string> = {
    timeout: m['admin.llms.health.errors.timeout'](),
    key_rejected: m['admin.llms.health.errors.keyRejected'](),
    no_credits: m['admin.llms.health.errors.noCredits'](),
    rate_limited: m['admin.llms.health.errors.rateLimited'](),
    model_not_found: m['admin.llms.health.errors.modelNotFound'](),
    empty_response: m['admin.llms.health.errors.emptyResponse'](),
    provider_error: m['admin.llms.health.errors.providerError'](),
    not_configured: m['admin.llms.health.errors.notConfigured'](),
    request_failed: m['admin.llms.health.errors.requestFailed']()
  }

  const llms = $derived(
    data.llms.map((llm) => ({
      ...llm,
      votes: data.data.models.find((other) => other.id === llm.id)?.data?.n_match,
      release_date: new Date(llm.release_date),
      updated_at: new Date(llm.updated_at!),
      created_at: new Date(llm.created_at!),
      id: llm.id!,
      custom_selectable: llm.custom_selectable !== false,
      // Numeric so the column sorts: failures first, then healthy, then untested.
      health: health.results.has(llm.id!)
        ? Number(!health.results.get(llm.id!)!.healthy)
        : undefined,
      search: toSearchString([llm.human_id, llm.name, llm.id!])
    }))
  )
  type DataKey = keyof Omit<(typeof llms)[number], 'links'>

  const cols = [
    { id: 'human_id', label: 'Human ID', orderable: true },
    { id: 'status', label: 'Status', orderable: true },
    { id: 'health', label: m['admin.llms.health.column'](), kind: 'number', orderable: true },
    { id: 'rate_limited', label: 'Rate limited', kind: 'boolean', orderable: true },
    { id: 'custom_selectable', label: 'Custom mode', kind: 'boolean', orderable: true },
    { id: 'release_date', label: 'Release date', kind: 'date', orderable: true },
    { id: 'created_at', label: 'Added', kind: 'date', orderable: true },
    { id: 'updated_at', label: 'Updated', kind: 'date', orderable: true },
    { id: 'id', label: 'UUID' },
    { id: 'votes', label: 'Vote count', kind: 'number', orderable: true }
  ] satisfies TableCol<DataKey>[]
  type ColKey = (typeof cols)[number]['id']

  let orderingCol = $state<ColKey>('human_id')
  let orderingMethod = $state<OrderingMethod>('descending')
  let search = $state('')

  $effect(() => {
    if (orderingCol === undefined) {
      orderingCol = 'human_id'
      orderingMethod = 'descending'
    }
  })

  const sortedRows = $derived(
    sortRows(llms, cols, { col: orderingCol, method: orderingMethod, search })
  )

  const enabledIds = $derived(llms.filter((llm) => llm.status === 'enabled').map((llm) => llm.id))
  const failedCount = $derived(
    [...health.results.values()].filter((result) => !result.healthy).length
  )
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
  {#snippet headerLeft()}
    <Link button icon="add-line" text={m['words.add']()} href={`${baseRoute}/create`} />
    <Button
      variant="secondary"
      disabled={health.running || !enabledIds.length}
      onclick={() => health.testAll(enabledIds)}
    >
      <Icon icon="i-ri-pulse-line" size="sm" class="mr-2" aria-hidden="true" />
      {m['admin.llms.health.button']()}
    </Button>
    <p class="fr-text--sm mb-0!" aria-live="polite">
      {#if health.running}
        {m['admin.llms.health.progress']({ done: health.results.size, total: health.total })}
      {:else if failedCount}
        {m['admin.llms.health.summaryFailed']({ failed: failedCount, total: health.total })}
      {:else if health.total}
        {m['admin.llms.health.summaryHealthy']()}
      {/if}
    </p>
  {/snippet}

  {#snippet cell(llm, col)}
    {#if col.id === 'human_id'}
      <a href={resolve(`${baseRoute}/${llm.id}`)}>{llm[col.id]}</a>
    {:else if col.id === 'status'}
      {@const status = llm[col.id]}
      <Badge
        size="sm"
        text={status}
        variant={status === 'enabled' ? 'green' : status === 'disabled' ? 'red' : ''}
      />
    {:else if col.id === 'health'}
      {@const result = health.results.get(llm.id)}
      {#if result}
        <span class="fr-text--sm mb-0! gap-1 flex items-center whitespace-nowrap">
          {#if result.healthy}
            <Icon icon="i-ri-check-line" size="sm" class="text-success" aria-label="OK" />
            {m['admin.llms.health.healthy']({ latency: result.latency_ms ?? 0 })}
          {:else if result.error}
            <Icon icon="i-ri-close-line" size="sm" class="text-error" aria-hidden="true" />
            <span class="text-error">{healthLabels[result.error]}</span>
          {/if}
        </span>
      {/if}
    {:else if col.id === 'rate_limited' || col.id === 'custom_selectable'}
      {#if llm[col.id]}
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
