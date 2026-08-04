<script lang="ts">
  import { dev } from '$app/environment'
  import PageLayout from '$components/PageLayout.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import ConversationActivityChart from './ConversationActivityChart.svelte'

  const { data } = $props()
  const numberFormatter = new Intl.NumberFormat(getLocale())
  const demoCounts = [18, 24, 21, 31, 28, 37, 35, 42, 39, 48, 44, 53, 49, 58]
  const hasActivity = $derived(data.statistics.daily_conversations.some((point) => point.count > 0))
  const showDemo = $derived(dev && !hasActivity)
  const activityPoints = $derived(
    showDemo
      ? data.statistics.daily_conversations.map((point, index) => ({
          ...point,
          count: demoCounts[index] ?? 0
        }))
      : data.statistics.daily_conversations
  )

  const metrics = $derived([
    {
      id: 'questions',
      emoji: '💬',
      value: data.statistics.questions_count,
      label: m['statistics.metrics.questions.label']()
    },
    {
      id: 'votes',
      emoji: '🗳️',
      value: data.statistics.votes_count,
      label: m['statistics.metrics.votes.label']()
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
    <h2 class="fr-h4 mb-6!">{m['statistics.overview']()}</h2>

    <dl class="metrics-grid">
      {#each metrics as metric (metric.id)}
        <div class="metric-card bg-very-light-primary">
          <span class="metric-emoji" aria-hidden="true">{metric.emoji}</span>
          <dt class="metric-label">{metric.label}</dt>
          <dd class="metric-value">{numberFormatter.format(metric.value)}</dd>
        </div>
      {/each}
    </dl>

    <p class="fr-text--sm mt-8! mb-0! text-grey">{m['statistics.methodology']()}</p>

    <section class="mt-12" aria-labelledby="activity-title">
      <h2 id="activity-title" class="fr-h4 mb-6!">{m['statistics.activity.sectionTitle']()}</h2>
      <ConversationActivityChart
        points={activityPoints}
        title={m['statistics.activity.title']()}
        description={m['statistics.activity.description']()}
        demoLabel={showDemo ? m['statistics.activity.demoLabel']() : undefined}
        tableLabel={m['statistics.activity.tableLabel']()}
        dateLabel={m['statistics.activity.dateLabel']()}
        conversationsLabel={m['statistics.activity.conversationsLabel']()}
      />
    </section>
  </section>
</PageLayout>

<style>
  .metrics-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.25rem;
    margin-inline: 0;
    padding-inline: 0;
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
    grid-row: 1 / 3;
    font-size: 1.75rem;
    line-height: 1;
  }

  .metric-value {
    grid-column: 2;
    grid-row: 1;
    align-self: end;
    justify-self: start;
    width: 100%;
    margin: 0;
    padding: 0;
    color: var(--text-title-grey);
    font-size: 2rem;
    font-weight: 700;
    line-height: 1;
    font-variant-numeric: tabular-nums;
    text-align: left;
  }

  .metric-label {
    grid-column: 2;
    grid-row: 2;
    align-self: start;
    justify-self: start;
    width: 100%;
    margin-top: 0.35rem;
    padding: 0;
    color: var(--text-title-grey);
    font-size: 0.875rem;
    line-height: 1.35;
    text-align: left;
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
