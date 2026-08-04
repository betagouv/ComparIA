<script lang="ts">
  import PageLayout from '$components/PageLayout.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'

  const { data } = $props()
  const numberFormatter = new Intl.NumberFormat(getLocale())

  const metrics = $derived([
    {
      id: 'questions',
      icon: 'fr-icon-question-answer-line',
      value: data.statistics.questions_count,
      label: m['statistics.metrics.questions.label'](),
      description: m['statistics.metrics.questions.description']()
    },
    {
      id: 'votes',
      icon: 'fr-icon-thumb-up-line',
      value: data.statistics.votes_count,
      label: m['statistics.metrics.votes.label'](),
      description: m['statistics.metrics.votes.description']()
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
    <dl class="gap-6 md:grid-cols-2 grid">
      {#each metrics as metric (metric.id)}
        <div class="metric-card cg-border bg-white p-6! md:p-8!">
          <div class="gap-3 flex items-center">
            <span class={[metric.icon, 'metric-icon']} aria-hidden="true"></span>
            <dt class="fr-h5 mb-0!">{metric.label}</dt>
          </div>
          <dd class="mt-6! mb-0!">
            <strong class="metric-value text-primary block">
              {numberFormatter.format(metric.value)}
            </strong>
            <span class="mt-3 text-grey block">{metric.description}</span>
          </dd>
        </div>
      {/each}
    </dl>

    <p class="fr-text--sm mt-8! mb-0! text-grey">{m['statistics.methodology']()}</p>
  </section>
</PageLayout>

<style>
  .metric-card {
    border-left: 0.5rem solid var(--border-action-high-blue-france);
  }

  .metric-icon {
    color: var(--text-action-high-blue-france);
  }

  .metric-value {
    font-size: clamp(2.5rem, 7vw, 4.5rem);
    line-height: 1;
    font-variant-numeric: tabular-nums;
  }
</style>
