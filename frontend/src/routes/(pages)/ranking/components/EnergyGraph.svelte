<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { SIZES, type BotModel } from '$lib/models'
  import { sortIfDefined } from '$lib/utils/data'
  import { extent, ticks } from 'd3-array'
  import { scaleLinear } from 'd3-scale'
  import { onMount } from 'svelte'

  type ModelGraphData = (typeof models)[number]

  let { data, onDownloadData }: { data: BotModel[]; onDownloadData: () => void } = $props()

  const dotSizes = { XS: 3, S: 5, M: 7, L: 9, XL: 11 } as const
  const archs = ['moe', 'dense', 'matformer', 'na'] as const
  const models = $derived(
    data
      .sort((a, b) => sortIfDefined(a, b, 'params'))
      .map((m) => {
        return {
          id: m.id,
          x: m.consumption_wh!,
          y: m.elo!,
          radius: dotSizes[m.friendly_size],
          class: m.license === 'proprietary' ? 'na' : m.arch
        }
      })
  )
  const ELOMedian = data[Math.floor(data.length / 2)].elo!

  // FIXME retrieve info from backend
  let lastUpdateDate = new Date()

  let hoveredModel = $state<string>()
  let tooltipPos = $state({ x: 0, y: 0 })
  const hoveredModelData = $derived(data.find((m) => m.id === hoveredModel))

  let svg = $state<SVGSVGElement>()
  let width = $state(1100)
  let height = $state(570)

  const padding = { top: 0, right: 5, bottom: 35, left: 40 }

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

  function onModelHover(model: ModelGraphData) {
    hoveredModel = model.id
    tooltipPos = { x: xScale(model.x), y: yScale(model.y) }
  }
</script>

<svelte:window onresize={resize} />

<div id="energy-graph" class="flex items-center gap-2">
  <div class="h-6 w-6 translate-y-[95px] -rotate-90 overflow-visible whitespace-nowrap text-center">
    <Icon icon="thumb-up-line" class="text-primary" />
    <strong>{m['ranking.energy.views.graph.yLabel']()}</strong>
  </div>

  <div class="relative flex-grow">
    <div class="flex">
      <svg bind:this={svg}>
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

        <!-- median -->
        <g transform="translate(0, {yScale(ELOMedian)})">
          <line class="elo-median" x1={padding.left} x2={xScale(minMaxX[1])} />
        </g>

        <!-- data -->
        {#each models as m}
          <circle
            cx={xScale(m.x)}
            cy={yScale(m.y)}
            r={m.radius}
            class={m.class}
            onpointerenter={() => onModelHover(m)}
            onpointerleave={() => (hoveredModel = undefined)}
          />
        {/each}
      </svg>

      {#if hoveredModelData}
        <div
          id="graph-tooltip"
          class="cg-border rounded-sm! absolute min-w-[175px] bg-white p-3"
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

      <div
        id="graph-legend"
        class="cg-border rounded-md! bg-very-light-grey h-[535px] w-[220px] p-4 text-[12px] leading-normal"
      >
        <p class="mb-4! text-[13px]!">
          <strong>{m['ranking.energy.views.graph.legends.arch']()}</strong>
        </p>
        <ul class="p-0! list-none! mb-10! font-medium">
          {#each archs as arch}
            <li class="p-0! mb-3 flex items-center">
              <div class={['dot me-2 rounded-full', arch]}></div>
              {m[`models.arch.types.${arch}.name`]()}
            </li>
          {/each}
        </ul>

        <p class="mb-4! text-[13px]! leading-tight!">
          <strong>{m['ranking.energy.views.graph.legends.size']()}</strong><br />
          <span class="text-[11px]">{m['ranking.energy.views.graph.legends.sizeSub']()}</span>
        </p>
        <ul class="p-0! list-none! font-medium">
          {#each SIZES as size}
            <li class="p-0! mb-3 flex items-center">
              <div
                class={['dot border-dark-grey me-2 rounded-full border']}
                style="--size: {dotSizes[size] * 2}px"
              ></div>
              {m[`models.size.count.${size}`]()}
            </li>
          {/each}
        </ul>
      </div>
    </div>

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
    href="#"
    download="true"
    text={m['ranking.table.downloadData']()}
    icon="download-line"
    iconPos="right"
    class="text-[14px]!"
    onclick={() => onDownloadData()}
  />
</div>

<style lang="postcss">
  #energy-graph {
    svg {
      width: 100%;
      height: 570px;
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

    .elo-median {
      stroke: var(--grey-625-425);
      stroke-dasharray: 5;
    }

    /* Dots color */
    .na {
      fill: #cecece;
      background-color: #cecece;
    }
    .moe {
      fill: var(--yellow-tournesol-850-200);
      background-color: var(--yellow-tournesol-850-200);
    }
    .dense {
      fill: #0a76f6;
      background-color: #0a76f6;
    }
    .matformer {
      fill: var(--green-menthe-850-200);
      background-color: var(--green-menthe-850-200);
    }
  }

  #graph-tooltip {
    top: var(--y);
    left: var(--x);
    transform: translate(-50%, calc(-100% - 0.75rem));
  }

  #graph-legend {
    .dot {
      min-width: var(--size, 16px);
      min-height: var(--size, 16px);
    }
  }
</style>
