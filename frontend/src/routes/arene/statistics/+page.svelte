<script lang="ts">
  import { resolve } from '$app/paths'
  import PageLayout from '$components/PageLayout.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import ConversationActivityChart from './ConversationActivityChart.svelte'

  const { data } = $props()
  const numberFormatter = new Intl.NumberFormat(getLocale())
  const periods = [
    { value: '7d', label: m['statistics.filters.sevenDays']() },
    { value: '30d', label: m['statistics.filters.thirtyDays']() },
    { value: '90d', label: m['statistics.filters.ninetyDays']() },
    { value: 'all', label: m['statistics.filters.allTime']() }
  ]
  const activityPoints = $derived(data.statistics.activity)
  const metrics = $derived([
    {
      id: 'prompts',
      emoji: '💬',
      value: data.statistics.prompts_count,
      label: m['statistics.metrics.prompts.label']()
    },
    {
      id: 'conversations',
      emoji: '🗣️',
      value: data.statistics.conversations_count,
      label: m['statistics.metrics.conversations.label']()
    },
    {
      id: 'models',
      emoji: '🤖',
      value: data.statistics.models_count,
      label: m['statistics.metrics.models.label']()
    }
  ])
</script>

<PageLayout
  seoTitle={m['statistics.title']()}
  title={m['statistics.title']()}
  subtitle={m['statistics.intro']()}
  bubble={m['statistics.eyebrow']()}
  class="bg-very-light-grey min-h-[calc(100vh-var(--second-header-size))]"
>
  <section class="fr-container py-4! md:py-8!" aria-label={m['statistics.title']()}>
    <nav class="period-filter mb-8" aria-label={m['statistics.filters.label']()}>
      <span class="fr-text--sm mb-0! font-bold">{m['statistics.filters.label']()}</span>
      <div class="period-links">
        {#each periods as period (period.value)}<a
            href={resolve(`/arene/statistics?period=${period.value}`)}
            aria-current={data.statistics.period === period.value ? 'page' : undefined}
            >{period.label}</a
          >{/each}
      </div>
    </nav>

    <h2 class="fr-h4 mb-6!">{m['statistics.overview']()}</h2>
    <dl class="metrics-grid">
      {#each metrics as metric (metric.id)}<div class="metric-card bg-very-light-primary">
          <span class="metric-emoji" aria-hidden="true">{metric.emoji}</span>
          <dt class="metric-label">{metric.label}</dt>
          <dd class="metric-value">{numberFormatter.format(metric.value)}</dd>
        </div>{/each}
    </dl>
    <section class="mt-12" aria-labelledby="activity-title">
      <h2 id="activity-title" class="fr-h4 mb-6!">{m['statistics.activity.sectionTitle']()}</h2>
      <ConversationActivityChart
        points={activityPoints}
        granularity={data.statistics.granularity}
        rangeStart={data.statistics.range_start}
        rangeEnd={data.statistics.range_end}
        title={m['statistics.activity.title']()}
        labels={{
          table: m['statistics.activity.tableLabel'](),
          date: m['statistics.activity.dateLabel'](),
          prompts: m['statistics.activity.promptsLabel'](),
          conversations: m['statistics.activity.conversationsLabel']()
        }}
      />
    </section>
  </section>
</PageLayout>

<style>
  .period-filter {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.75rem 1rem;
  }
  .period-links {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }
  .period-links a {
    background: white;
    border: 1px solid var(--brand-primary);
    border-radius: 999px;
    padding: 0.4rem 0.8rem;
    background-image: none;
    font-size: 0.875rem;
  }
  .period-links a[aria-current='page'] {
    background: var(--brand-primary);
    color: white;
  }
  .metrics-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.25rem;
    margin: 0;
    padding: 0;
  }
  .metric-card {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: auto auto;
    column-gap: 0.75rem;
    align-items: center;
    min-height: 6.5rem;
    padding: 1rem;
    border: 1px solid var(--border-default-blue-france);
    border-radius: 1rem;
  }
  .metric-emoji {
    grid-row: 1/3;
    font-size: 1.75rem;
    line-height: 1;
  }
  .metric-value {
    grid-column: 2;
    grid-row: 1;
    align-self: end;
    margin: 0;
    padding: 0;
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
  }
  .metric-label {
    grid-column: 2;
    grid-row: 2;
    align-self: start;
    margin-top: 0.35rem;
    font-size: 0.875rem;
  }
  @media (min-width: 48em) {
    .metrics-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  @media (min-width: 78em) {
    .metrics-grid {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
  }
</style>
