<script lang="ts">
  import { onMount } from 'svelte'
  import { scaleLinear } from 'd3-scale'
  import { getModelsContext } from '$lib/models'
  import { extent, ticks } from 'd3-array'

  const modelsData = getModelsContext()

  const points = $derived(
    modelsData
      .filter((m) => !!m.elo)
      .map((m) => ({
        x: m.consumption_wh!,
        y: m.elo!
      }))
  )

  let svg = $state<SVGSVGElement>()
  let width = $state(500)
  let height = $state(700)

  const padding = { top: 0, right: 0, bottom: 40, left: 40 }

  const minMaxX = $derived.by(() => {
    const [min, max] = extent(points, (p) => p.x) as [number, number]
    return [min - 5, max + 15] as const
  })
  const minMaxY = $derived.by(() => {
    const [min, max] = extent(points, (p) => p.y) as [number, number]
    return [min - 5, max + 35] as const
  })
  const xScale = $derived(scaleLinear(minMaxX, [padding.left, width - padding.right]))
  const yScale = $derived(scaleLinear(minMaxY, [height - padding.bottom, padding.top]))
  const xTicks = $derived(ticks(...minMaxX, 7))
  const yTicks = $derived(ticks(...minMaxY, 9))

  onMount(resize)

  function resize() {
    ;({ width, height } = svg!.getBoundingClientRect())
  }
</script>

<svelte:window onresize={resize} />

<svg id="energy-graph" bind:this={svg}>
  <!-- y axis -->
  <g class="axis y-axis">
    {#each yTicks as tick}
      <g transform="translate(0, {yScale(tick)})">
        <line x1={padding.left} x2={xScale(minMaxX[1])} />
        <text x={padding.left - 8} y="+4">{tick}</text>
      </g>
    {/each}
  </g>

  <!-- x axis -->
  <g class="axis x-axis">
    {#each xTicks as tick}
      <g transform="translate({xScale(tick)},0)">
        <line y1={yScale(minMaxY[0])} y2={yScale(minMaxY[1])} />
        <text y={height - padding.bottom + 20}>{tick}</text>
      </g>
    {/each}
  </g>

  <!-- data -->
  {#each points as point}
    <circle cx={xScale(point.x)} cy={yScale(point.y)} r="5" />
  {/each}
</svg>

<style lang="postcss">
  #energy-graph {
    & {
      width: 100%;
      height: 700px;
    }

    .axis {
      line {
        stroke: var(--grey-950-100);
      }

      text {
        font-size: 14px;
      }
    }

    .x-axis text {
      text-anchor: middle;
    }

    .y-axis text {
      text-anchor: end;
    }
  }
</style>
