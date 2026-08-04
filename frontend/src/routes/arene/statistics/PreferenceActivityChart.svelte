<script lang="ts">
  import { scaleBand, scaleLinear } from 'd3'
  import type { PreferenceCounts } from './+page'
  type Point = { date: string } & PreferenceCounts
  type Key = keyof PreferenceCounts
  let { points, title, description, labels } = $props<{
    points: Point[]
    title: string
    description: string
    labels: Record<Key, string> & {
      table: string
      date: string
      proportions: string
      numbers: string
    }
  }>()
  let display = $state<'proportions' | 'numbers'>('proportions')
  const keys: Key[] = ['a_better', 'b_better', 'both_good', 'both_bad']
  const width = 960,
    height = 350,
    margin = { top: 20, right: 24, bottom: 48, left: 56 }
  const totals = $derived(points.map((p: Point) => keys.reduce((sum, key) => sum + p[key], 0)))
  const maxTotal = $derived(Math.max(1, ...totals))
  const x = $derived(
    scaleBand<string>()
      .domain(points.map((p: Point) => p.date))
      .range([margin.left, width - margin.right])
      .padding(0.22)
  )
  const y = $derived(
    scaleLinear()
      .domain([0, display === 'proportions' ? 100 : maxTotal])
      .nice(4)
      .range([height - margin.bottom, margin.top])
  )
  const ticks = $derived(y.ticks(4))
  const formatDate = (value: string) =>
    new Intl.DateTimeFormat(undefined, { day: 'numeric', month: 'short' }).format(
      new Date(`${value}T12:00:00`)
    )
  const segment = (point: Point, key: Key, index: number) => {
    const total = keys.reduce((sum, k) => sum + point[k], 0)
    const values = keys.map((k) =>
      display === 'proportions' ? (total ? (point[k] / total) * 100 : 0) : point[k]
    )
    const before = values.slice(0, index).reduce((a, b) => a + b, 0)
    return {
      y: y(before + values[index]),
      height: y(before) - y(before + values[index]),
      value: point[key],
      ratio: total ? (point[key] / total) * 100 : 0
    }
  }
</script>

<figure class="chart-panel bg-very-light-primary">
  <figcaption>
    <h3 id="preference-chart-title" class="fr-h5 mb-1!">{title}</h3>
    <p id="preference-chart-description" class="mb-0! text-grey">{description}</p>
  </figcaption>
  <div class="toolbar mt-4">
    <div class="fr-segmented">
      <div class="fr-segmented__elements">
        <button
          class:active={display === 'proportions'}
          aria-pressed={display === 'proportions'}
          type="button"
          onclick={() => (display = 'proportions')}>{labels.proportions}</button
        ><button
          class:active={display === 'numbers'}
          aria-pressed={display === 'numbers'}
          type="button"
          onclick={() => (display = 'numbers')}>{labels.numbers}</button
        >
      </div>
    </div>
  </div>
  <div class="legend mt-4">
    {#each keys as key (key)}<span><i class={key}></i>{labels[key]}</span>{/each}
  </div>
  <div class="mt-4 overflow-x-auto">
    <svg
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-labelledby="preference-chart-title preference-chart-description"
      class="chart"
    >
      {#each ticks as tick (tick)}<line
          x1={margin.left}
          x2={width - margin.right}
          y1={y(tick)}
          y2={y(tick)}
          class="grid-line"
        /><text x={margin.left - 12} y={y(tick) + 5} text-anchor="end" class="axis-label"
          >{tick}{display === 'proportions' ? ' %' : ''}</text
        >{/each}
      {#each points as point (point.date)}<g
          >{#each keys as key, index (key)}{@const item = segment(point, key, index)}<rect
              x={x(point.date)}
              y={item.y}
              width={x.bandwidth()}
              height={Math.max(0, item.height)}
              class={key}
              ><title
                >{formatDate(point.date)} — {labels[key]}: {item.value} ({item.ratio.toFixed(1)} %)</title
              ></rect
            >{/each}<text
            x={(x(point.date) ?? 0) + x.bandwidth() / 2}
            y={height - 14}
            text-anchor="middle"
            class="axis-label">{formatDate(point.date)}</text
          ></g
        >{/each}
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
                  ><th scope="col">{labels.date}</th>{#each keys as key (key)}<th scope="col"
                      >{labels[key]}</th
                    >{/each}</tr
                ></thead
              ><tbody
                >{#each points as point (point.date)}<tr
                    ><td>{formatDate(point.date)}</td>{#each keys as key (key)}<td>{point[key]}</td
                      >{/each}</tr
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
  .axis-label {
    fill: var(--text-mention-grey);
    font-size: 0.8rem;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    font-size: 0.875rem;
  }
  .legend span {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
  .legend i {
    display: block;
    width: 0.8rem;
    height: 0.8rem;
  }
  .a_better {
    fill: #6a6af4;
    background: #6a6af4;
  }
  .b_better {
    fill: #8585f6;
    background: #8585f6;
  }
  .both_good {
    fill: #00a95f;
    background: #00a95f;
  }
  .both_bad {
    fill: #e1000f;
    background: #e1000f;
  }
  .fr-segmented__elements {
    display: flex;
  }
  .fr-segmented button {
    border: 1px solid var(--border-action-high-blue-france);
    padding: 0.5rem 0.75rem;
    background: white;
    color: var(--text-action-high-blue-france);
  }
  .fr-segmented button:first-child {
    border-radius: 0.5rem 0 0 0.5rem;
  }
  .fr-segmented button:last-child {
    border-radius: 0 0.5rem 0.5rem 0;
  }
  .fr-segmented button.active {
    background: var(--background-action-high-blue-france);
    color: white;
  }
  @media (max-width: 47.99em) {
    .chart-panel {
      padding: 1rem;
    }
  }
</style>
