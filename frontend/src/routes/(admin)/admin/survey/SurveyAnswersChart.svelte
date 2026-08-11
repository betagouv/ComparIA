<script lang="ts">
  import type { AdminSurveyQuestion } from '$lib/generated/admin'
  import { m } from '$lib/i18n/messages'

  let {
    question,
    defaultLocale,
    title
  }: { question: AdminSurveyQuestion; defaultLocale: string; title: string } = $props()

  const titleId = $props.id()

  // Archived options keep their answers, so they stay on the chart: dropping
  // them would quietly change the totals an admin is reading.
  const slices = $derived(
    question.options.map((option, index) => ({
      key: option.key,
      label: option.labels[defaultLocale] ?? Object.values(option.labels)[0] ?? option.key,
      archived: option.archived,
      count: option.answer_count,
      colour: `var(--survey-series-${index % 6})`
    }))
  )
  const total = $derived(slices.reduce((sum, slice) => sum + slice.count, 0))
  const share = (count: number) => (total ? Math.round((count / total) * 100) : 0)

  // A single-choice question splits one population into parts of a whole,
  // which is what a doughnut reads well. A checkbox group does not: its
  // options overlap and sum past 100%, so bars are the honest shape there.
  const isSingleChoice = $derived(question.input_type === 'select')

  const radius = 80
  const circumference = 2 * Math.PI * radius
  const arcs = $derived(
    slices.reduce<{ slice: (typeof slices)[number]; offset: number; length: number }[]>(
      (acc, slice) => {
        const used = acc.reduce((sum, arc) => sum + arc.length, 0)
        return [
          ...acc,
          {
            slice,
            offset: used,
            length: total ? (slice.count / total) * circumference : 0
          }
        ]
      },
      []
    )
  )
</script>

<figure class="chart-panel bg-very-light-primary">
  <figcaption class="gap-2 flex flex-wrap items-baseline justify-between">
    <h3 id={titleId} class="fr-h6 mb-0!">{title}</h3>
    <span class="fr-text--sm text-grey">
      {m['survey.admin.respondentCount']({ count: question.respondent_count })}
    </span>
  </figcaption>

  {#if total === 0}
    <p class="fr-text--sm mt-4! mb-0! text-grey">{m['survey.admin.noAnswersYet']()}</p>
  {:else if isSingleChoice}
    <div class="doughnut-row mt-4">
      <svg viewBox="0 0 220 220" role="img" aria-labelledby={titleId} class="doughnut">
        {#each arcs as arc (arc.slice.key)}
          <circle
            cx="110"
            cy="110"
            r={radius}
            fill="none"
            stroke={arc.slice.colour}
            stroke-width="34"
            stroke-dasharray={`${arc.length} ${circumference - arc.length}`}
            stroke-dashoffset={-arc.offset}
            transform="rotate(-90 110 110)"
          />
        {/each}
        <text x="110" y="104" text-anchor="middle" class="doughnut-total">{total}</text>
        <text x="110" y="126" text-anchor="middle" class="doughnut-caption">
          {m['survey.admin.answersLabel']()}
        </text>
      </svg>

      <ul class="legend">
        {#each slices as slice (slice.key)}
          <li>
            <i style="background: {slice.colour}"></i>
            <span class={{ 'text-grey line-through': slice.archived }}>{slice.label}</span>
            <b>{share(slice.count)}%</b>
            <span class="count text-grey">({slice.count})</span>
          </li>
        {/each}
      </ul>
    </div>
  {:else}
    <ul class="bars mt-4" role="img" aria-labelledby={titleId}>
      {#each slices as slice (slice.key)}
        <li>
          <span class="bar-label {slice.archived ? 'text-grey line-through' : ''}">
            {slice.label}
          </span>
          <span class="bar-track">
            <span class="bar-fill" style="width: {share(slice.count)}%; background: {slice.colour}"
            ></span>
          </span>
          <span class="bar-value">
            <b>{share(slice.count)}%</b>
            <span class="count text-grey">({slice.count})</span>
          </span>
        </li>
      {/each}
    </ul>
  {/if}
</figure>

<style>
  .chart-panel {
    padding: 1.5rem;
    border: 1px solid var(--border-default-blue-france);
    border-radius: 1rem;
    margin: 0;
    /* Reused by both shapes, and by every question on the page, so the same
       option index always gets the same colour. */
    --survey-series-0: var(--brand-primary, #000091);
    --survey-series-1: #6a6af4;
    --survey-series-2: #21ab8e;
    --survey-series-3: #e4794a;
    --survey-series-4: #a558a0;
    --survey-series-5: #417dc4;
  }
  .doughnut-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 1.5rem;
  }
  .doughnut {
    width: 11rem;
    height: 11rem;
    flex: none;
  }
  .doughnut-total {
    font-size: 2rem;
    font-weight: 700;
    fill: var(--text-title-grey);
  }
  .doughnut-caption {
    font-size: 0.8rem;
    fill: var(--text-mention-grey);
  }
  .legend {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin: 0;
    padding: 0;
    list-style: none;
    min-width: 14rem;
    flex: 1;
  }
  .legend li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
  }
  .legend i {
    width: 0.75rem;
    height: 0.75rem;
    border-radius: 0.25rem;
    flex: none;
  }
  .legend b {
    margin-left: auto;
  }
  .bar-value {
    display: flex;
    align-items: baseline;
    gap: 0.35rem;
    font-size: 0.875rem;
  }
  .count {
    font-size: 0.8125rem;
  }
  .bars {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .bars li {
    display: grid;
    grid-template-columns: minmax(6rem, 12rem) 1fr auto;
    align-items: center;
    gap: 0.75rem;
  }
  .bar-label {
    font-size: 0.875rem;
  }
  .bar-track {
    background: var(--background-contrast-grey);
    border-radius: 999px;
    height: 0.75rem;
    overflow: hidden;
  }
  .bar-fill {
    display: block;
    height: 100%;
    border-radius: 999px;
  }
  @media (max-width: 40rem) {
    .bars li {
      grid-template-columns: 1fr auto;
    }
    .bar-track {
      grid-column: 1 / -1;
    }
  }
</style>
