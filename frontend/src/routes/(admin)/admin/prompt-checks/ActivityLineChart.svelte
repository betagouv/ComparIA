<script lang="ts">
  import type { PromptCheckDecision, PromptCheckTimelinePoint } from './types'

  let {
    points,
    labels,
    colors
  }: {
    points: PromptCheckTimelinePoint[]
    labels: Record<PromptCheckDecision, string>
    colors: Record<PromptCheckDecision, string>
  } = $props()

  const series: PromptCheckDecision[] = ['logged', 'warned', 'blocked', 'error']
  const width = 760
  const height = 250
  const left = 42
  const right = 14
  const top = 14
  const bottom = 36
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom
  const maxValue = $derived(
    Math.max(1, ...points.flatMap((point) => series.map((key) => point.by_decision[key] ?? 0)))
  )

  function x(index: number) {
    return left + (points.length <= 1 ? plotWidth / 2 : (index / (points.length - 1)) * plotWidth)
  }

  function y(value: number) {
    return top + plotHeight - (value / maxValue) * plotHeight
  }

  function tickLabel(ratio: number) {
    const value = maxValue * ratio
    return maxValue <= 2 ? Number(value.toFixed(1)).toLocaleString('fr-FR') : Math.round(value)
  }

  function pathFor(decision: PromptCheckDecision) {
    return points
      .map(
        (point, index) =>
          `${index === 0 ? 'M' : 'L'} ${x(index)} ${y(point.by_decision[decision] ?? 0)}`
      )
      .join(' ')
  }

  function shortDate(value: string) {
    return new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short' }).format(
      new Date(`${value}T00:00:00`)
    )
  }

  const labelIndexes = $derived(
    points.length < 2
      ? [0]
      : [...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1])]
  )
</script>

<figure class="m-0!">
  <div class="gap-x-5 gap-y-2 mb-4 flex flex-wrap" aria-label="Légende du graphique">
    {#each series as decision (decision)}
      <span class="gap-2 text-xs text-grey flex items-center">
        <span class="size-2.5 rounded-full" style="background: {colors[decision]}"></span>
        {labels[decision]}
      </span>
    {/each}
  </div>

  {#if points.length === 0}
    <div class="h-56 text-sm text-grey flex items-center justify-center">
      Aucune détection sur cette période.
    </div>
  {:else}
    <svg
      viewBox={`0 0 ${width} ${height}`}
      class="h-auto w-full overflow-visible"
      role="img"
      aria-label="Évolution des messages surveillés, prévenus, refusés et en échec"
    >
      {#each [0, 0.5, 1] as ratio (ratio)}
        {@const tickY = top + plotHeight - ratio * plotHeight}
        <line x1={left} x2={width - right} y1={tickY} y2={tickY} class="grid-line" />
        <text x={left - 9} y={tickY + 4} text-anchor="end" class="axis-label">
          {tickLabel(ratio)}
        </text>
      {/each}

      {#each series as decision (decision)}
        <path
          d={pathFor(decision)}
          fill="none"
          stroke={colors[decision]}
          stroke-width="3"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
        {#each points as point, index (`${decision}-${point.date}`)}
          <circle
            cx={x(index)}
            cy={y(point.by_decision[decision] ?? 0)}
            r="3"
            fill={colors[decision]}
          >
            <title
              >{shortDate(point.date)} — {labels[decision]} : {point.by_decision[decision] ??
                0}</title
            >
          </circle>
        {/each}
      {/each}

      {#each labelIndexes as index (index)}
        <text x={x(index)} y={height - 8} text-anchor="middle" class="axis-label">
          {shortDate(points[index].date)}
        </text>
      {/each}
    </svg>
  {/if}
</figure>

<style>
  .grid-line {
    stroke: var(--border-default-grey);
    stroke-width: 1;
    stroke-dasharray: 3 5;
  }

  .axis-label {
    fill: var(--text-mention-grey);
    font-size: 12px;
  }
</style>
