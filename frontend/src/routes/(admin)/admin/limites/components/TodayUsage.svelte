<script lang="ts">
  import { resolve } from '$app/paths'
  import { Alert, Badge, Table } from '$components/dsfr'
  import type { DailyCapProposal, LLMDailyUsage } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import type { TableCol } from '$lib/utils/data'

  let {
    usage,
    proposals
  }: {
    /** Each enabled model's day, null when it could not be read. */
    usage: LLMDailyUsage[] | null
    /** The daily caps "Calibrer" proposes, while its results show. */
    proposals?: DailyCapProposal[]
  } = $props()

  const locale = getLocale()
  const numbers = new Intl.NumberFormat(locale)
  const percents = new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 0 })
  const dollars = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: 'USD',
    currencyDisplay: 'narrowSymbol',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })

  const proposed = $derived(new Map((proposals ?? []).map((cap) => [cap.llm_id, cap])))
  const rows = $derived((usage ?? []).map((llm) => ({ ...llm, id: llm.llm_id })))

  type ColId = 'name' | 'estimated_usd' | 'cap_usd' | 'cache' | 'proposed'
  const cols = $derived.by((): TableCol<ColId>[] => {
    const cols: TableCol<ColId>[] = [
      { id: 'name', label: m['admin.limits.today.model']() },
      { id: 'estimated_usd', label: m['admin.limits.today.spent'](), kind: 'number' },
      { id: 'cap_usd', label: m['admin.limits.today.cap'](), kind: 'number' },
      { id: 'cache', label: m['admin.limits.today.cache'](), kind: 'number' }
    ]
    if (proposals) cols.push({ id: 'proposed', label: m['admin.limits.today.proposed']() })
    return cols
  })

  function proposal(cap: DailyCapProposal) {
    return m['admin.limits.today.proposal']({
      value: dollars.format(cap.value),
      percentile: String(cap.percentile),
      days: String(cap.days),
      highest: dollars.format(cap.highest)
    })
  }
</script>

<section aria-labelledby="limits-today">
  <h2 id="limits-today" class="fr-h5 mb-1!">{m['admin.limits.today.title']()}</h2>
  <p class="fr-text--sm mb-3! text-[--text-mention-grey]">{m['admin.limits.today.intro']()}</p>

  {#if usage === null}
    <Alert variant="error" title={m['admin.limits.today.failed']()} small />
  {:else if !usage.length}
    <p class="fr-text--sm mb-0!">{m['admin.limits.today.empty']()}</p>
  {:else}
    <Table
      id="limits-today-table"
      caption={m['admin.limits.today.caption']()}
      hideCaption
      {cols}
      {rows}
    >
      {#snippet cell(llm, col)}
        {#if col.id === 'name'}
          <span class="gap-2 flex flex-wrap items-center">
            <a href={resolve(`/admin/llms/llms/${llm.llm_id}`)}>{llm.name}</a>
            {#if llm.resting}
              <Badge
                size="sm"
                variant="orange"
                text={m['admin.limits.today.resting']()}
                noTooltip
              />
            {/if}
          </span>
        {:else if col.id === 'estimated_usd'}
          {dollars.format(llm.estimated_usd)}
        {:else if col.id === 'cap_usd'}
          {llm.cap_usd === null ? m['admin.limits.today.noCap']() : dollars.format(llm.cap_usd)}
        {:else if col.id === 'cache'}
          {llm.answers
            ? m['admin.limits.today.cacheShare']({
                share: percents.format(llm.cached_answers / llm.answers),
                count: numbers.format(llm.answers)
              })
            : m['admin.limits.today.noAnswer']()}
        {:else if col.id === 'proposed'}
          {@const cap = proposed.get(llm.llm_id)}
          {#if cap}
            <span class="fr-text--sm mb-0!">{proposal(cap)}</span>
          {:else}
            {m['admin.limits.today.noProposal']()}
          {/if}
        {/if}
      {/snippet}
    </Table>
  {/if}
</section>
