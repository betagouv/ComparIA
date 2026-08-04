<script lang="ts">
  import { curveMonotoneX, line, scaleLinear, scalePoint } from 'd3'

  export type ActivityPoint = { date: string; prompts: number; conversations: number }
  let { points, title, description, demoLabel, labels } = $props<{
    points: ActivityPoint[]
    title: string
    description: string
    demoLabel?: string
    labels: { table: string; date: string; prompts: string; conversations: string }
  }>()

  const width = 960
  const height = 340
  const margin = { top: 24, right: 24, bottom: 48, left: 56 }
  const xScale = $derived(
    scalePoint<string>()
      .domain(points.map((p: ActivityPoint) => p.date))
      .range([margin.left, width - margin.right])
  )
  const maxCount = $derived(
    Math.max(1, ...points.flatMap((p: ActivityPoint) => [p.prompts, p.conversations]))
  )
  const yScale = $derived(
    scaleLinear()
      .domain([0, maxCount])
      .nice(4)
      .range([height - margin.bottom, margin.top])
  )
  const yTicks = $derived(yScale.ticks(4))
  const xTickIndexes = $derived(
    points.length
      ? [
          ...new Set([
            0,
            Math.floor((points.length - 1) / 3),
            Math.floor(((points.length - 1) * 2) / 3),
            points.length - 1
          ])
        ]
      : []
  )
  const makePath = (key: 'prompts' | 'conversations') =>
    line<ActivityPoint>()
      .x((p) => xScale(p.date) ?? 0)
      .y((p) => yScale(p[key]))
      .curve(curveMonotoneX)(points) ?? ''
  const formatDate = (value: string) =>
    new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' }).format(
      new Date(`${value}T12:00:00`)
    )
</script>

<figure class="chart-panel bg-very-light-primary">
  <figcaption class="gap-3 sm:flex-row sm:items-start sm:justify-between flex flex-col">
    <div>
      <h3 id="activity-chart-title" class="fr-h5 mb-1!">{title}</h3>
      <p id="activity-chart-description" class="mb-0! text-grey">{description}</p>
    </div>
    {#if demoLabel}<p class="fr-badge fr-badge--sm fr-badge--info mb-0!">{demoLabel}</p>{/if}
  </figcaption>
  <div class="legend mt-4" aria-hidden="true">
    <span><i class="prompts"></i>{labels.prompts}</span><span
      ><i class="conversations"></i>{labels.conversations}</span
    >
  </div>
  <div class="mt-4 overflow-x-auto">
    <svg
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-labelledby="activity-chart-title activity-chart-description"
      class="chart"
    >
      {#each yTicks as tick (tick)}
        <line
          x1={margin.left}
          x2={width - margin.right}
          y1={yScale(tick)}
          y2={yScale(tick)}
          class="grid-line"
        />
        <text x={margin.left - 12} y={yScale(tick) + 5} text-anchor="end" class="axis-label"
          >{tick}</text
        >
      {/each}
      <line
        x1={margin.left}
        x2={width - margin.right}
        y1={height - margin.bottom}
        y2={height - margin.bottom}
        class="axis-line"
      />
      {#each xTickIndexes as index (index)}<text
          x={xScale(points[index].date)}
          y={height - 14}
          text-anchor="middle"
          class="axis-label">{formatDate(points[index].date)}</text
        >{/each}
      <path d={makePath('prompts')} class="activity-line prompts-line" />
      <path d={makePath('conversations')} class="activity-line conversations-line" />
      {#each points as point (point.date)}
        <circle
          cx={xScale(point.date)}
          cy={yScale(point.prompts)}
          r="4"
          class="activity-point prompts-point"
          ><title>{formatDate(point.date)}: {point.prompts} {labels.prompts}</title></circle
        >
        <circle
          cx={xScale(point.date)}
          cy={yScale(point.conversations)}
          r="4"
          class="activity-point conversations-point"
          ><title>{formatDate(point.date)}: {point.conversations} {labels.conversations}</title
          ></circle
        >
      {/each}
    </svg>
  </div>
  <details class="mt-4">
    <summary class="fr-link cursor-pointer">{labels.table}</summary>
    <div class="fr-table fr-table--bordered mt-3">
      <div class="fr-table__wrapper">
        <div class="fr-table__container">
          <div class="fr-table__content">
            <table>
              <thead
                ><tr
                  ><th scope="col">{labels.date}</th><th scope="col">{labels.prompts}</th><th
                    scope="col">{labels.conversations}</th
                  ></tr
                ></thead
              ><tbody
                >{#each points as point (point.date)}<tr
                    ><td>{formatDate(point.date)}</td><td>{point.prompts}</td><td
                      >{point.conversations}</td
                    ></tr
                  >{/each}</tbody
              >
            </table>
          </div>
        </div>
      </div>
    </div>
  </details>
</figure>

<style>
  .chart-panel {
    padding: 1.5rem;
    border: 1px solid var(--border-default-blue-france);
    border-radius: 1rem;
  }
  .chart {
    display: block;
    min-width: 42rem;
    width: 100%;
    height: auto;
  }
  .grid-line {
    stroke: var(--border-default-blue-france);
    stroke-opacity: 0.35;
    stroke-dasharray: 4 5;
  }
  .axis-line {
    stroke: var(--border-default-blue-france);
    stroke-opacity: 0.65;
  }
  .axis-label {
    fill: var(--text-mention-grey);
    font-size: 0.875rem;
  }
  .activity-line {
    fill: none;
    stroke-width: 3;
  }
  .prompts-line {
    stroke: var(--border-action-high-blue-france);
  }
  .conversations-line {
    stroke: #e1000f;
  }
  .activity-point {
    stroke: white;
    stroke-width: 2;
  }
  .prompts-point {
    fill: var(--background-action-high-blue-france);
  }
  .conversations-point {
    fill: #e1000f;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 1.25rem;
    font-size: 0.875rem;
  }
  .legend span {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .legend i {
    display: block;
    width: 0.9rem;
    height: 0.9rem;
    border-radius: 50%;
  }
  .legend .prompts {
    background: var(--background-action-high-blue-france);
  }
  .legend .conversations {
    background: #e1000f;
  }
  @media (max-width: 47.99em) {
    .chart-panel {
      padding: 1rem;
    }
  }
</style>
