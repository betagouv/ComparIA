<script lang="ts">
  import type { PromptCheckDecision } from './types'

  let {
    categories,
    categoryLabel,
    labels,
    colors
  }: {
    categories: Record<string, Partial<Record<PromptCheckDecision, number>>>
    categoryLabel: (category: string) => string
    labels: Record<PromptCheckDecision, string>
    colors: Record<PromptCheckDecision, string>
  } = $props()

  const series: PromptCheckDecision[] = ['logged', 'warned', 'blocked', 'error']
  const rows = $derived(
    Object.entries(categories)
      .map(([category, counts]) => ({
        category,
        counts,
        total: series.reduce((sum, decision) => sum + (counts[decision] ?? 0), 0)
      }))
      .filter((row) => row.total > 0)
      .sort((a, b) => b.total - a.total)
  )
  const max = $derived(Math.max(1, ...rows.map((row) => row.total)))
</script>

{#if rows.length === 0}
  <p class="text-sm text-grey">Aucune catégorie ne s'est déclenchée sur la période.</p>
{:else}
  <ul class="gap-4 m-0! p-0! flex list-none flex-col" aria-label="Détections par catégorie">
    {#each rows as row (row.category)}
      <li id={`prompt-check-stats-category-${row.category}`}>
        <div class="gap-3 mb-1.5 text-sm flex items-baseline">
          <span class="text-grey min-w-0 flex-1">{categoryLabel(row.category)}</span>
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
