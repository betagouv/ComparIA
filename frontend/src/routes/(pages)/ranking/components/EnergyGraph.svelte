<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getModelsContext } from '$lib/models'
  import { extent, ticks } from 'd3-array'
  import { scaleLinear } from 'd3-scale'
  import { onMount } from 'svelte'

  const modelsData = getModelsContext()

  const models = $derived(
    modelsData
      .filter((m) => !!m.elo)
      .map((m) => ({
        id: m.id,
        x: m.consumption_wh!,
        y: m.elo!,
        class: m.license === 'proprietary' ? 'proprietary' : m.friendly_size
      }))
  )
  // FIXME retrieve info from backend
  let lastUpdateDate = new Date()

  let hoveredModel = $state<string>()
  let tooltipPos = $state({ x: 0, y: 0 })
  const hoveredModelData = $derived(modelsData.find((m) => m.id === hoveredModel))

  let svg = $state<SVGSVGElement>()
  let width = $state(1100)
  let height = $state(700)

  const padding = { top: 0, right: 0, bottom: 35, left: 40 }

  const minMaxX = $derived.by(() => {
    const [min, max] = extent(models, (m) => m.x) as [number, number]
    return [min - 5, max + 15] as const
  })
  const minMaxY = $derived.by(() => {
    const [min, max] = extent(models, (m) => m.y) as [number, number]
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

  function onModelHover(model: (typeof models)[number]) {
    hoveredModel = model.id
    tooltipPos = { x: xScale(model.x), y: yScale(model.y) }
  }
</script>

<svelte:window onresize={resize} />

<div class="flex items-center gap-2">
  <div class="h-6 w-6 translate-y-[95px] -rotate-90 overflow-visible whitespace-nowrap text-center">
    <Icon icon="thumb-up-line" class="text-primary" />
    <strong>{m['ranking.energy.views.graph.yLabel']()}</strong>
  </div>
  <div class="relative flex-grow">
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
      {#each models as m}
        <circle
          cx={xScale(m.x)}
          cy={yScale(m.y)}
          r="5"
          class={m.class}
          onpointerenter={() => onModelHover(m)}
          onpointerleave={() => (hoveredModel = undefined)}
        />
      {/each}
    </svg>

    {#if hoveredModelData}
      <div
        id="graph-tooltip"
        class="cg-border rounded-sm! absolute bg-white p-3"
        style="--x: {tooltipPos.x}px; --y:{tooltipPos.y}px;"
      >
        <div class="flex">
          <img
            src="/orgs/ai/{hoveredModelData.icon_path}"
            alt={hoveredModelData.organisation}
            class="me-1 w-[14px] object-contain"
          />
          <strong class="text-[12px]">{hoveredModelData.id}</strong>
        </div>

        <div class="mt-1 text-[10px]">
          <div class="flex gap-1 leading-relaxed">
            <Icon icon="thumb-up-line" size="xxs" class="text-primary" />
            <p class="mb-0! text-[10px]! text-grey leading-relaxed!">
              {m['ranking.energy.views.graph.tooltip.elo']()}
            </p>
            <strong class="ms-auto">{hoveredModelData.elo}</strong>
          </div>
          <div class="flex gap-1 leading-relaxed">
            <Icon icon="flashlight-line" size="xxs" class="text-primary" />
            <p class="mb-0! text-[10px]! text-grey leading-relaxed!">
              {m['ranking.energy.views.graph.tooltip.conso']()}
            </p>
            <strong class="ms-auto">{hoveredModelData.consumption_wh}</strong>
          </div>
        </div>
      </div>
    {/if}

    <div class="text-center">
      <Icon icon="flashlight-line" class="text-primary" />
      <strong>{m['ranking.energy.views.graph.xLabel']()}</strong>
    </div>
  </div>
</div>

<div class="flex gap-3 pb-9 pt-6">
  <p class="mb-0! text-[14px]! text-grey">
    {m['ranking.table.lastUpdate']({ date: lastUpdateDate.toLocaleDateString() })}
  </p>

  <!-- FIXME 404 -->
  <Link
    native={false}
    href="/data/ranking.csv"
    download="true"
    text={m['ranking.table.downloadData']()}
    icon="download-line"
    iconPos="right"
    class="text-[14px]!"
  />
</div>

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

    circle {
      &.proprietary {
        fill: #cecece;
      }
      &.XS {
        fill: var(--green-emeraude-main-632);
      }
      &.S {
        fill: var(--green-emeraude-850-200);
      }
      &.M {
        fill: var(--red-marianne-850-200);
      }
      &.L {
        fill: var(--orange-terre-battue-main-645);
      }
      &.XL {
        fill: var(--red-marianne-main-472);
      }
    }
  }

  #graph-tooltip {
    top: var(--y);
    left: var(--x);
    transform: translate(-50%, calc(-100% - 0.75rem));
  }
</style>
