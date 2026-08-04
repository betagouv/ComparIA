<script lang="ts">
  import PageLayout from '$components/PageLayout.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'

  const { data } = $props()
  const numberFormatter = new Intl.NumberFormat(getLocale())

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
  </section>
</PageLayout>

<style>
  .metrics-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 1.25rem;
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
