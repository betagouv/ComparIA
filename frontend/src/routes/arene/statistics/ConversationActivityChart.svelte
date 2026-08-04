<script lang="ts">
  import { curveMonotoneX, line, scaleLinear, scalePoint } from 'd3'

  export type ActivityPoint = { date: string; count: number }

  let {
    points,
    title,
    description,
    demoLabel,
    tableLabel,
    dateLabel,
    conversationsLabel
  }: {
    points: ActivityPoint[]
    title: string
    description: string
    demoLabel?: string
    tableLabel: string
    dateLabel: string
    conversationsLabel: string
  } = $props()

  const width = 960
  const height = 340
  const margin = { top: 24, right: 24, bottom: 48, left: 56 }

  const xScale = $derived(
    scalePoint<string>()
      .domain(points.map((point) => point.date))
      .range([margin.left, width - margin.right])
  )
  const maxCount = $derived(Math.max(1, ...points.map((point) => point.count)))
  const yScale = $derived(
    scaleLinear()
      .domain([0, maxCount])
      .nice(4)
      .range([height - margin.bottom, margin.top])
  )
  const yTicks = $derived(yScale.ticks(4))
  const xTickIndexes = $derived(
    [...new Set([0, 3, 6, 9, Math.max(0, points.length - 1)])].filter(
      (index) => index < points.length
    )
  )
  const path = $derived(
    line<ActivityPoint>()
      .x((point) => xScale(point.date) ?? 0)
      .y((point) => yScale(point.count))
      .curve(curveMonotoneX)(points) ?? ''
  )

  const formatDate = (value: string) =>
    new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' }).format(
      new Date(`${value}T12:00:00`)
    )
</script>

<figure class="chart-panel bg-white">
  <figcaption>
    <div class="gap-3 sm:flex-row sm:items-start sm:justify-between flex flex-col">
      <div>
        <h3 id="activity-chart-title" class="fr-h5 mb-1!">{title}</h3>
        <p id="activity-chart-description" class="mb-0! text-grey">{description}</p>
      </div>
      {#if demoLabel}
        <p class="demo-label fr-badge fr-badge--sm fr-badge--info mb-0!">{demoLabel}</p>
      {/if}
    </div>
  </figcaption>

  <div class="mt-6 overflow-x-auto">
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
        <text x={margin.left - 12} y={yScale(tick) + 5} text-anchor="end" class="axis-label">
          {tick}
        </text>
      {/each}

      <line
        x1={margin.left}
        x2={width - margin.right}
        y1={height - margin.bottom}
        y2={height - margin.bottom}
        class="axis-line"
      />

      {#each xTickIndexes as index (index)}
        <text
          x={xScale(points[index].date)}
          y={height - 14}
          text-anchor="middle"
          class="axis-label"
        >
          {formatDate(points[index].date)}
        </text>
      {/each}

      <path d={path} class="activity-line" />
      {#each points as point (point.date)}
        <circle cx={xScale(point.date)} cy={yScale(point.count)} r="5" class="activity-point">
          <title>{formatDate(point.date)}: {point.count} {conversationsLabel}</title>
        </circle>
      {/each}
    </svg>
  </div>

  <details class="mt-4">
    <summary class="fr-link cursor-pointer">{tableLabel}</summary>
    <div class="fr-table fr-table--bordered mt-3" data-fr-js-table="true">
      <div class="fr-table__wrapper">
        <div class="fr-table__container">
          <div class="fr-table__content">
            <table>
              <thead>
                <tr><th scope="col">{dateLabel}</th><th scope="col">{conversationsLabel}</th></tr>
              </thead>
              <tbody>
                {#each points as point (point.date)}
                  <tr><td>{formatDate(point.date)}</td><td>{point.count}</td></tr>
                {/each}
              </tbody>
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
    border: 1px solid var(--border-default-grey);
  }

  .chart {
    display: block;
    min-width: 42rem;
    width: 100%;
    height: auto;
  }

  .grid-line {
    stroke: var(--border-default-grey);
    stroke-dasharray: 4 5;
  }

  .axis-line {
    stroke: var(--border-plain-grey);
  }

  .axis-label {
    fill: var(--text-mention-grey);
    font-size: 0.875rem;
  }

  .activity-line {
    fill: none;
    stroke: var(--border-action-high-blue-france);
    stroke-width: 3;
  }

  .activity-point {
    fill: var(--background-action-high-blue-france);
    stroke: white;
    stroke-width: 2;
  }

  .demo-label {
    flex: none;
  }

  @media (max-width: 47.99em) {
    .chart-panel {
      padding: 1rem;
    }
  }
</style>
