<script lang="ts">
  import { goto } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Segmented, Select } from '$components/dsfr'
  import type { ActivityFilterOptions } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'
  import { PERIODS, label, nextQuery } from '../filters'

  let { options }: { options: ActivityFilterOptions } = $props()

  // Two filters only: when and which model. Mode, cohort, dates and archived
  // conversations still work from the address, for a link that needs them.
  const params = $derived(page.url.searchParams)
  const custom = $derived(!params.get('period') && !!(params.get('start') || params.get('end')))
  const period = $derived(custom ? '' : (params.get('period') ?? '30d'))

  const periodOptions = PERIODS.map((value) => ({
    value,
    label: label('filters.periodsShort', value)
  }))
  const modelOptions = $derived([
    { value: '', label: m['admin.activity.filters.allModels']() },
    ...options.llms.map((llm) => ({ value: llm.id, label: llm.name }))
  ])

  const tab = $derived(page.url.pathname.endsWith('/conversations') ? 'conversations' : 'apercu')

  function update(changes: Record<string, string | null>) {
    goto(resolve(`/admin/activite/${tab}${nextQuery(page.url.searchParams, changes)}`), {
      keepFocus: true,
      noScroll: true
    })
  }

  function onPeriod(value: string) {
    if (value === period) return
    update({ period: value === '30d' ? null : value, start: null, end: null })
  }
</script>

<section
  class="activity-filters gap-x-3 gap-y-2 mb-6 flex flex-wrap items-center"
  aria-label={m['admin.activity.filters.label']()}
>
  <Segmented
    id="activity-period"
    legend={m['admin.activity.filters.period']()}
    hideLegend
    size="sm"
    options={periodOptions}
    value={period}
    onchange={(event) => onPeriod((event.target as HTMLInputElement).value)}
  />
  <Select
    id="activity-model"
    label={m['admin.activity.filters.model']()}
    hideLabel
    options={modelOptions}
    selected={params.get('llm_id') ?? ''}
    onchange={(event) => update({ llm_id: event.currentTarget.value })}
    groupClass="mb-0!"
  />
</section>

<style>
  .activity-filters :global(.fr-segmented) {
    max-width: 100%;
    overflow-x: auto;
  }
</style>
