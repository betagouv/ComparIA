<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import type { PromptCheckDecision } from './types'

  let {
    byCriterion,
    criterionLabel,
    labels,
    colors
  }: {
    byCriterion: Record<string, Partial<Record<PromptCheckDecision, number>>>
    criterionLabel: (key: string) => string
    labels: Record<PromptCheckDecision, string>
    colors: Record<PromptCheckDecision, string>
  } = $props()

  const series: PromptCheckDecision[] = ['logged', 'warned', 'blocked', 'error']
  const rows = $derived(
    Object.entries(byCriterion)
      .map(([key, counts]) => ({
        key,
        counts,
        total: series.reduce((sum, decision) => sum + (counts[decision] ?? 0), 0)
      }))
      .filter((row) => row.total > 0)
      .sort((a, b) => b.total - a.total)
  )
  const max = $derived(Math.max(1, ...rows.map((row) => row.total)))
</script>

{#if rows.length === 0}
  <p class="text-sm text-grey">{m['admin.promptChecks.stats.byCriterionNone']()}</p>
{:else}
  <ul
    class="gap-4 m-0! p-0! flex list-none flex-col"
    aria-label={m['admin.promptChecks.stats.byCriterionTitle']()}
  >
    {#each rows as row (row.key)}
      <li id={`prompt-check-stats-criterion-${row.key}`}>
        <div class="gap-3 mb-1.5 text-sm flex items-baseline">
          <span class="text-grey min-w-0 flex-1">{criterionLabel(row.key)}</span>
          <strong class="text-dark-grey tabular-nums">{row.total}</strong>
        </div>
        <div
          class="h-5 rounded-sm flex overflow-hidden bg-[--background-contrast-grey]"
          style="width: {(row.total / max) * 100}%"
        >
          {#each series as decision (decision)}
            {@const count = row.counts[decision] ?? 0}
            {#if count > 0}
              <span
                style="width: {(count / row.total) * 100}%; background: {colors[decision]}"
                title={`${labels[decision]} : ${count}`}
              ></span>
            {/if}
          {/each}
        </div>
      </li>
    {/each}
  </ul>
{/if}
