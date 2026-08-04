<script lang="ts">
  import { dev } from '$app/environment'
  import { resolve } from '$app/paths'
  import PageLayout from '$components/PageLayout.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import ConversationActivityChart from './ConversationActivityChart.svelte'
  import PreferenceActivityChart from './PreferenceActivityChart.svelte'
  import { SvelteDate } from 'svelte/reactivity'

  const { data } = $props()
  const numberFormatter = new Intl.NumberFormat(getLocale())
  const percentFormatter = new Intl.NumberFormat(getLocale(), { maximumFractionDigits: 1 })
  const periods = [
    { value: '7d', label: m['statistics.filters.sevenDays']() },
    { value: '30d', label: m['statistics.filters.thirtyDays']() },
    { value: '90d', label: m['statistics.filters.ninetyDays']() },
    { value: 'all', label: m['statistics.filters.allTime']() }
  ]
  const demoPrompts = [28, 35, 31, 44, 40, 53, 49, 61, 57, 68, 63, 74, 70, 81]
  const demoConversations = [18, 24, 21, 31, 28, 37, 35, 42, 39, 48, 44, 53, 49, 58]
  const demoPreferences = [
    [8, 5, 3, 2],
    [10, 7, 4, 3],
    [8, 6, 5, 2],
    [13, 9, 5, 4],
    [11, 8, 6, 3],
    [15, 11, 7, 4],
    [14, 10, 7, 4],
    [17, 12, 8, 5],
    [15, 12, 8, 4],
    [19, 14, 9, 6],
    [18, 12, 9, 5],
    [21, 16, 10, 6],
    [19, 15, 10, 5],
    [23, 17, 11, 7]
  ]
  const demoDates = Array.from({ length: 14 }, (_, index) => {
    const date = new SvelteDate()
    date.setDate(date.getDate() - (13 - index))
    return date.toISOString().slice(0, 10)
  })
  const showDemo = $derived(
    dev && !data.statistics.activity.some((point) => point.prompts > 0 || point.conversations > 0)
  )
  const demoStart = $derived(data.statistics.period === '7d' ? 7 : 0)
  const activityPoints = $derived(
    showDemo
      ? demoDates.slice(demoStart).map((date, slicedIndex) => {
          const index = slicedIndex + demoStart
          return {
            date,
            prompts: demoPrompts[index],
            conversations: demoConversations[index]
          }
        })
      : data.statistics.activity
  )
  const preferencePoints = $derived(
    showDemo
      ? demoDates.slice(demoStart).map((date, slicedIndex) => {
          const index = slicedIndex + demoStart
          return {
            date,
            a_better: demoPreferences[index][0],
            b_better: demoPreferences[index][1],
            both_good: demoPreferences[index][2],
            both_bad: demoPreferences[index][3]
          }
        })
      : data.statistics.preference_activity
  )
  const preferenceCounts = $derived(
    showDemo
      ? preferencePoints.reduce(
          (totals, point) => ({
            a_better: totals.a_better + point.a_better,
            b_better: totals.b_better + point.b_better,
            both_good: totals.both_good + point.both_good,
            both_bad: totals.both_bad + point.both_bad
          }),
          { a_better: 0, b_better: 0, both_good: 0, both_bad: 0 }
        )
      : data.statistics.preferences
  )
  const preferenceTotal = $derived(
    Object.values(preferenceCounts).reduce((sum, value) => sum + value, 0)
  )
  const metrics = $derived([
    {
      id: 'prompts',
      emoji: '💬',
      value: showDemo
        ? activityPoints.reduce((sum, point) => sum + point.prompts, 0)
        : data.statistics.prompts_count,
      label: m['statistics.metrics.prompts.label']()
    },
    {
      id: 'conversations',
      emoji: '🗨️',
      value: showDemo
        ? activityPoints.reduce((sum, point) => sum + point.conversations, 0)
        : data.statistics.conversations_count,
      label: m['statistics.metrics.conversations.label']()
    },
    {
      id: 'models',
      emoji: '🤖',
      value: showDemo ? 31 : data.statistics.models_count,
      label: m['statistics.metrics.models.label']()
    }
  ])
  const preferenceCards = $derived([
    { key: 'a_better', icon: '←', label: m['statistics.preferences.aBetter']() },
    { key: 'b_better', icon: '→', label: m['statistics.preferences.bBetter']() },
    { key: 'both_good', icon: '👍', label: m['statistics.preferences.bothGood']() },
    { key: 'both_bad', icon: '👎', label: m['statistics.preferences.bothBad']() }
  ] as const)
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
    <p class="fr-text--sm mt-6! mb-0! text-grey">{m['statistics.methodology']()}</p>

    <section class="mt-12" aria-labelledby="activity-title">
      <h2 id="activity-title" class="fr-h4 mb-6!">{m['statistics.activity.sectionTitle']()}</h2>
      <ConversationActivityChart
        points={activityPoints}
        title={m['statistics.activity.title']()}
        description={m['statistics.activity.description']()}
        demoLabel={showDemo ? m['statistics.activity.demoLabel']() : undefined}
        labels={{
          table: m['statistics.activity.tableLabel'](),
          date: m['statistics.activity.dateLabel'](),
          prompts: m['statistics.activity.promptsLabel'](),
          conversations: m['statistics.activity.conversationsLabel']()
        }}
      />
    </section>

    <section class="mt-12" aria-labelledby="preferences-title">
      <div class="section-heading">
        <div>
          <h2 id="preferences-title" class="fr-h4 mb-1!">
            {m['statistics.preferences.sectionTitle']()}
          </h2>
          <p class="mb-0! text-grey">
            {m['statistics.preferences.total']({ count: numberFormatter.format(preferenceTotal) })}
          </p>
        </div>
      </div>
      <dl class="preference-grid mt-6">
        {#each preferenceCards as card (card.key)}{@const count = preferenceCounts[card.key]}
          <div class="preference-card bg-very-light-primary">
            <span class="preference-icon" aria-hidden="true">{card.icon}</span>
            <dt>{card.label}</dt>
            <dd>
              <strong>{numberFormatter.format(count)}</strong><span
                >{preferenceTotal ? percentFormatter.format((count / preferenceTotal) * 100) : 0} %</span
              >
            </dd>
          </div>{/each}
      </dl>
      <div class="mt-8">
        <PreferenceActivityChart
          points={preferencePoints}
          title={m['statistics.preferences.chartTitle']()}
          description={m['statistics.preferences.chartDescription']()}
          labels={{
            a_better: m['statistics.preferences.aBetter'](),
            b_better: m['statistics.preferences.bBetter'](),
            both_good: m['statistics.preferences.bothGood'](),
            both_bad: m['statistics.preferences.bothBad'](),
            table: m['statistics.activity.tableLabel'](),
            date: m['statistics.activity.dateLabel'](),
            proportions: m['statistics.preferences.proportions'](),
            numbers: m['statistics.preferences.numbers']()
          }}
        />
      </div>
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
    border: 1px solid var(--border-action-high-blue-france);
    border-radius: 999px;
    padding: 0.4rem 0.8rem;
    background-image: none;
    font-size: 0.875rem;
  }
  .period-links a[aria-current='page'] {
    background: var(--background-action-high-blue-france);
    color: white;
  }
  .metrics-grid,
  .preference-grid {
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
  .preference-card {
    display: grid;
    grid-template-columns: auto 1fr;
    grid-template-rows: auto auto;
    gap: 0.25rem 0.75rem;
    padding: 1rem;
    border: 1px solid var(--border-default-blue-france);
    border-radius: 1rem;
  }
  .preference-icon {
    grid-row: 1/3;
    align-self: center;
    font-size: 1.5rem;
  }
  .preference-card dt {
    font-size: 0.875rem;
  }
  .preference-card dd {
    display: flex;
    align-items: baseline;
    gap: 0.5rem;
    margin: 0;
  }
  .preference-card strong {
    font-size: 1.5rem;
  }
  .preference-card dd span {
    color: var(--text-mention-grey);
    font-size: 0.875rem;
  }
  @media (min-width: 48em) {
    .metrics-grid,
    .preference-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  @media (min-width: 78em) {
    .metrics-grid,
    .preference-grid {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
  }
</style>
