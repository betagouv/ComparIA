<script lang="ts">
  import { curveMonotoneX, line, scaleLinear, scalePoint } from 'd3'
  import { getLocale } from '$lib/i18n/runtime'

  export type ActivityPoint = {
    date: string
    prompts: number
    conversations: number
    /** The period still under way, with what it should hold once full. */
    partial?: boolean
    projected_prompts?: number | null
    projected_conversations?: number | null
  }
  type Series = 'prompts' | 'conversations'
  let {
    points,
    title,
    labels,
    granularity,
    rangeStart,
    rangeEnd,
    compact = false
  } = $props<{
    points: ActivityPoint[]
    title: string
    labels: {
      table: string
      date: string
      prompts: string
      conversations: string
      ongoing: string
      estimate: string
    }
    granularity: 'hour' | 'day' | 'week' | 'month'
    rangeStart: string
    rangeEnd: string
    /** No panel and a shorter plot, for a page where the chart is one block
     *  among several and the section heading already names it. */
    compact?: boolean
  }>()

  const titleId = $props.id()
  const dateFormatter = $derived(
    new Intl.DateTimeFormat(getLocale(), { day: 'numeric', month: 'short' })
  )

  const width = 960
  const height = $derived(compact ? 220 : 340)
  const margin = { top: 24, right: 24, bottom: 48, left: 56 }
  const xScale = $derived(
    scalePoint<string>()
      .domain(points.map((p: ActivityPoint) => p.date))
      .range([margin.left, width - margin.right])
  )
  // The period still under way is not drawn as it stands: half a day next to
  // full days reads as a collapse. The line stops at the last full period and
  // a dotted segment runs to the estimate, when there is one.
  const fullPoints = $derived(points.filter((p: ActivityPoint) => !p.partial))
  const current = $derived(points.find((p: ActivityPoint) => p.partial))
  const projected = (key: Series) =>
    current?.[key === 'prompts' ? 'projected_prompts' : 'projected_conversations'] ?? null
  const maxCount = $derived(
    Math.max(
      1,
      ...fullPoints.flatMap((p: ActivityPoint) => [p.prompts, p.conversations]),
      projected('prompts') ?? 0,
      projected('conversations') ?? 0
    )
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
  const makePath = (key: Series) =>
    line<ActivityPoint>()
      .x((p) => xScale(p.date) ?? 0)
      .y((p) => yScale(p[key]))
      .curve(curveMonotoneX)(fullPoints) ?? ''
  const estimatePath = (key: Series) => {
    const last = fullPoints.at(-1)
    const value = projected(key)
    if (!current || value === null) return ''
    const end = `${xScale(current.date) ?? 0},${yScale(value)}`
    return last ? `M${xScale(last.date) ?? 0},${yScale(last[key])} L${end}` : `M${end}`
  }
  const numberFormatter = new Intl.NumberFormat(getLocale())
  const estimateText = (key: Series) => {
    const value = projected(key)
    return value === null
      ? `${numberFormatter.format(current?.[key] ?? 0)} (${labels.ongoing})`
      : `≈ ${numberFormatter.format(value)} (${labels.estimate}, ${numberFormatter.format(current?.[key] ?? 0)} ${labels.ongoing})`
  }
  // A bucket date is its first day, so week buckets are shown as the range they cover.
  // Hourly buckets carry their hour already ('2026-10-05T14:00').
  const formatDate = (value: string) => {
    if (granularity === 'hour') {
      return new Intl.DateTimeFormat(getLocale(), { hour: '2-digit', minute: '2-digit' }).format(
        new Date(value)
      )
    }
    const start = new Date(`${value}T12:00:00`)
    if (granularity === 'month') {
      return new Intl.DateTimeFormat(getLocale(), { month: 'long', year: 'numeric' }).format(start)
    }
    if (granularity === 'week') {
      const selectedStart = new Date(`${rangeStart}T12:00:00`)
      const selectedEnd = new Date(`${rangeEnd}T12:00:00`)
      const visibleStart = new Date(Math.max(start.getTime(), selectedStart.getTime()))
      const end = new Date(Math.min(start.getTime() + 6 * 86_400_000, selectedEnd.getTime()))
      return dateFormatter.formatRange(visibleStart, end)
    }
    return dateFormatter.format(start)
  }
</script>

<figure class={compact ? 'm-0!' : 'chart-panel bg-very-light-primary'}>
  <figcaption>
    <h3 id={titleId} class={compact ? 'sr-only' : 'fr-h5 mb-0!'}>{title}</h3>
  </figcaption>
  <div class={['legend', compact ? 'legend--compact' : 'mt-4']} aria-hidden="true">
    <span><span class="swatch prompts"></span>{labels.prompts}</span><span
      ><span class="swatch conversations"></span>{labels.conversations}</span
    >{#if current && (projected('prompts') !== null || projected('conversations') !== null)}<span
        ><span class="swatch estimate"></span>{labels.estimate}</span
      >{/if}
  </div>
  <!-- Focusable: the chart is wider than the box on small screens, and a
       keyboard user with no stop inside it can never scroll to the right.
       The lint rule below cannot see that it scrolls. -->
  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
  <div
    class={['chart-scroller overflow-x-auto', compact ? 'mt-2' : 'mt-4']}
    tabindex="0"
    role="group"
    aria-labelledby={titleId}
  >
    <svg
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-labelledby={titleId}
      aria-describedby="{titleId}-table"
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
      {#each ['prompts', 'conversations'] as const as key (key)}
        {@const value = projected(key)}
        {#if current && value !== null}
          <path d={estimatePath(key)} class="estimate-line {key}-estimate" />
          <circle
            cx={xScale(current.date)}
            cy={yScale(value)}
            r="5"
            class="estimate-point {key}-estimate"
            ><title>{formatDate(current.date)}: {estimateText(key)} {labels[key]}</title></circle
          >
        {/if}
      {/each}
      {#each fullPoints as point (point.date)}
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
  <details class={compact ? 'mt-1' : 'mt-4'} id="{titleId}-table">
    <summary class={['fr-link cursor-pointer', { 'fr-link--sm': compact }]}>{labels.table}</summary>
    <div class="fr-table fr-table--bordered mt-3">
      <div class="fr-table__wrapper">
        <div class="fr-table__container">
          <div class="fr-table__content">
            <table>
              <caption class="fr-sr-only">{title}</caption>
              <thead
                ><tr
                  ><th scope="col">{labels.date}</th><th scope="col">{labels.prompts}</th><th
                    scope="col">{labels.conversations}</th
                  ></tr
                ></thead
              ><tbody
                >{#each points as point (point.date)}<tr
                    >{#if point.partial}<td>{formatDate(point.date)} ({labels.ongoing})</td><td
                        >{estimateText('prompts')}</td
                      ><td>{estimateText('conversations')}</td>{:else}<td
                        >{formatDate(point.date)}</td
                      ><td>{point.prompts}</td><td>{point.conversations}</td>{/if}</tr
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
  .chart-scroller:focus-visible {
    outline: 2px solid var(--outline-color);
    outline-offset: 2px;
  }
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
    stroke: var(--text-mention-grey);
    stroke-opacity: 0.45;
    stroke-dasharray: 4 5;
  }
  /* Grey, not the brand blue at 65%: that rendered ~#9696f7 on the panel,
     2.19:1, and the baseline is the zero reference of the graph. */
  .axis-line {
    stroke: var(--text-mention-grey);
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
    stroke: var(--brand-primary);
  }
  /* Dashed as well as red: blue against red is the common colour-blind
     confusion pair, and the two lines sit at 1.10:1 against each other. */
  .conversations-line {
    stroke: var(--red-marianne-main-472);
    stroke-dasharray: 8 5;
  }
  .activity-point {
    stroke: white;
    stroke-width: 2;
  }
  .prompts-point {
    fill: var(--brand-primary);
  }
  .conversations-point {
    fill: var(--red-marianne-main-472);
  }
  /* Dotted and paler than the measured lines, with hollow markers: an
     estimate, not a count. */
  .estimate-line {
    fill: none;
    stroke-width: 2;
    stroke-dasharray: 2 5;
    stroke-linecap: round;
    opacity: 0.7;
  }
  .estimate-point {
    fill: white;
    stroke-width: 2;
  }
  .prompts-estimate {
    stroke: var(--brand-primary);
  }
  .conversations-estimate {
    stroke: var(--red-marianne-main-472);
  }
  .legend .estimate {
    background: white;
    border: 2px dotted var(--text-mention-grey);
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 1.25rem;
    font-size: 0.875rem;
  }
  .legend--compact {
    gap: 1rem;
    font-size: 0.75rem;
    color: var(--text-mention-grey);
  }
  .legend span {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .legend .swatch {
    display: block;
    width: 0.9rem;
    height: 0.9rem;
    border-radius: 50%;
  }
  /* Mirrors the dashed line: the legend must not rely on hue either. */
  .legend .conversations {
    border-radius: 0;
  }
  .legend .prompts {
    background: var(--brand-primary);
  }
  .legend .conversations {
    background: var(--red-marianne-main-472);
  }
  @media (max-width: 47.99em) {
    .chart-panel {
      padding: 1rem;
    }
  }
</style>
