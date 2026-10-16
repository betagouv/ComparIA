<script lang="ts">
  import { resolve } from '$app/paths'
  import { Alert, Badge, Icon, Table } from '$components/dsfr'
  import { usdFormatter } from '$lib/currency'
  import type { DailyCapProposal, LLMDailyUsage } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import { FULL_ICON } from '$lib/limits.svelte'
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
  const dollars = usdFormatter(locale)

  const proposed = $derived(new Map((proposals ?? []).map((cap) => [cap.llm_id, cap])))
  // The models worth a look: those that cost something today, have a cap,
  // or get a proposed one. The rest are only counted.
  const shown = $derived(
    (usage ?? []).filter(
      (llm) => llm.estimated_usd > 0 || llm.cap_usd !== null || proposed.has(llm.llm_id)
    )
  )
  const rows = $derived(shown.map((llm) => ({ ...llm, id: llm.llm_id })))
  const idle = $derived((usage?.length ?? 0) - shown.length)

  type ColId = 'name' | 'estimated_usd' | 'cache' | 'proposed'
  const cols = $derived.by((): TableCol<ColId>[] => {
    const cols: TableCol<ColId>[] = [
      { id: 'name', label: m['admin.limits.today.model']() },
      // One column for the spend and its cap, so the figure that matters fits
      // on a phone.
      { id: 'estimated_usd', label: m['admin.limits.today.spent'](), kind: 'number' },
      { id: 'cache', label: m['admin.limits.today.cache'](), kind: 'number' }
    ]
    if (proposals) cols.push({ id: 'proposed', label: m['admin.limits.today.proposed']() })
    return cols
  })

  // Under a cent reads as spent, not as nothing.
  function spent(usd: number) {
    return usd > 0 && usd < 0.005
      ? m['admin.limits.today.underCent']({ value: dollars.format(0.01) })
      : dollars.format(usd)
  }

  // How the caps were proposed, told once under the table.
  const rule = $derived.by(() => {
    const first = proposals?.[0]
    if (!first) return undefined
    return m['admin.limits.today.proposalRule']({
      percentile: String(first.percentile),
      days: String(first.days)
    })
  })
</script>

<section aria-labelledby="limits-today">
  <h2 id="limits-today" class="fr-h5 mb-1!">{m['admin.limits.today.title']()}</h2>
  <p class="fr-text--sm mb-3! text-[--text-mention-grey]">{m['admin.limits.today.intro']()}</p>

  {#if usage === null}
    <Alert variant="error" title={m['admin.limits.today.failed']()} small />
  {:else if !shown.length}
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
            {#if llm.full}
              <!-- The arena's word and icon for it; a state, not an error. -->
              <Badge size="sm" class="normal-case!">
                <Icon icon={FULL_ICON} size="xs" block class="me-1" />
                {m['admin.limits.today.full']()}
              </Badge>
            {/if}
          </span>
        {:else if col.id === 'estimated_usd'}
          {llm.cap_usd === null
            ? m['admin.limits.today.spentNoCap']({ spent: spent(llm.estimated_usd) })
            : m['admin.limits.today.spentOfCap']({
                spent: spent(llm.estimated_usd),
                cap: dollars.format(llm.cap_usd)
              })}
          {#if !llm.counted && (llm.cap_usd !== null || proposed.has(llm.llm_id))}
            <span class="fr-text--xs mb-0! font-bold min-w-40 block whitespace-normal">
              {m['admin.limits.today.notCounted']()}
            </span>
          {/if}
        {:else if col.id === 'cache'}
          {@const share = percents.format(llm.cached_answers / llm.answers)}
          {#if llm.answers > 1}
            {m['admin.limits.today.cacheShare']({ share, count: numbers.format(llm.answers) })}
          {:else if llm.answers}
            {m['admin.limits.today.cacheShareOne']({ share })}
          {:else}
            {m['admin.limits.today.noAnswer']()}
          {/if}
        {:else if col.id === 'proposed'}
          {@const cap = proposed.get(llm.llm_id)}
          {#if cap}
            <span class="flex flex-col">
              <strong>{dollars.format(cap.value)}</strong>
              <span class="fr-text--xs mb-0! text-[--text-mention-grey]">
                {m['admin.limits.today.highest']({ value: dollars.format(cap.highest) })}
              </span>
              {#if cap.value <= llm.estimated_usd}
                <span class="fr-text--xs mb-0! font-bold">
                  {m['admin.limits.today.restsAtOnce']()}
                </span>
              {/if}
            </span>
          {:else}
            {m['admin.limits.today.noProposal']()}
          {/if}
        {/if}
      {/snippet}
    </Table>
  {/if}
  {#if rule}
    <p class="fr-text--sm mb-0! mt-2!">{rule}</p>
  {/if}
  {#if shown.length && idle}
    <p class="fr-text--sm mb-0! mt-2! text-[--text-mention-grey]">
      {idle > 1
        ? m['admin.limits.today.idle']({ count: numbers.format(idle) })
        : m['admin.limits.today.idleOne']()}
    </p>
  {/if}
</section>
