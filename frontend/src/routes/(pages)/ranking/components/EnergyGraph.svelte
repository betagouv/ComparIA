<script lang="ts">
  import { Icon, Link, Select } from '$components/dsfr'
  import Checkbox from '$components/dsfr/Checkbox.svelte'
  import { m } from '$lib/i18n/messages'
  import { SIZES, type BotModel } from '$lib/models'
  import { sortIfDefined } from '$lib/utils/data'
  import { extent, ticks } from 'd3-array'
  import { scaleLinear } from 'd3-scale'
  import { onMount } from 'svelte'

  type ModelGraphData = (typeof models)[number]

  let { data, onDownloadData }: { data: BotModel[]; onDownloadData: () => void } = $props()

  let dotMode = $state<'arch' | 'size' | 'params'>('size')
  let useActiveParams = $state(false)
  const dotModeOpts = [
    { value: 'size' as const, label: 'ELO / Conso (taille)' },
    { value: 'arch' as const, label: 'ELO / Conso (arch)' },
    { value: 'params' as const, label: 'ELO / Paramètres (conso)' }
  ]

  function getConsoClass(c: number) {
    if (c > 200) return 'XL'
    if (c >= 100) return 'L'
    if (c > 25) return 'M'
    if (c > 5) return 'S'
    return 'XS'
  }

  const models = $derived(
    data
      .sort((a, b) => sortIfDefined(a, b, 'params'))
      .filter((m) => (dotMode === 'params' && useActiveParams ? !!m.active_params : true))
      .map((m) => {
        const radius =
          dotMode === 'arch' ? ({ XS: 3, S: 5, M: 7, L: 9, XL: 11 } as const)[m.friendly_size] : 5
        const klass =
          dotMode === 'arch'
            ? m.arch.replace('maybe-', '')
            : dotMode === 'params'
              ? getConsoClass(m.active_params!)
              : m.license === 'proprietary'
                ? 'proprietary'
                : m.friendly_size
        return {
          id: m.id,
          x: dotMode === 'params' ? m.params : m.consumption_wh!,
          y: m.elo!,
          radius,
          class: klass
        }
      })
  )
  const ELOMedian = data[Math.floor(data.length / 2)].elo!

  const legend = $derived.by(() => {
    if (dotMode === 'arch')
      return {
        legend: 'Architectures',
        elems: ['moe', 'dense', 'matformer'].map((arch) => ({
          class: arch,
          label: arch
        }))
      }
    if (dotMode === 'params')
      return {
        legend: 'Consommation (wh)',
        elems: [
          { class: 'XL', label: 'XL : > 200Wh' },
          { class: 'L', label: 'L : >= 100Wh' },
          { class: 'M', label: 'M : > 25Wh' },
          { class: 'S', label: 'S : > 5Wh' },
          { class: 'XS', label: 'XS : <= 5Wh' }
        ]
      }
    return {
      legend: m['models.list.filters.size.legend'](),
      elems: [
        ...SIZES.map((size) => ({
          class: size,
          label: `${size} : ${m[`models.list.filters.size.labels.${size}`]()}`
        })),
        {
          class: 'proprietary',
          label: m['ranking.energy.views.graph.legendProprietary']()
        }
      ]
    }
  })

  // FIXME retrieve info from backend
  let lastUpdateDate = new Date()

  let hoveredModel = $state<string>()
  let tooltipPos = $state({ x: 0, y: 0 })
  const hoveredModelData = $derived(data.find((m) => m.id === hoveredModel))

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

  function onModelHover(model: ModelGraphData) {
    hoveredModel = model.id
    tooltipPos = { x: xScale(model.x), y: yScale(model.y) }
  }
</script>

<svelte:window onresize={resize} />

<div class="mb-10 flex items-center gap-4">
  <Select
    id="dot-mode"
    label="Représentation des points"
    bind:selected={dotMode}
    options={dotModeOpts}
    groupClass="flex items-end gap-3"
    class="w-auto!"
  />
  {#if dotMode === 'params'}
    <Checkbox id="active-params" bind:checked={useActiveParams} label="Utiliser active_params" />
  {/if}
</div>

<div id="energy-graph" class="flex items-center gap-2">
  <div class="h-6 w-6 translate-y-[95px] -rotate-90 overflow-visible whitespace-nowrap text-center">
    <Icon icon="thumb-up-line" class="text-primary" />
    <strong>{m['ranking.energy.views.graph.yLabel']()}</strong>
  </div>
  <div class="relative flex-grow">
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

          <div class="mt-4 flex gap-1 leading-relaxed">
            <p class="mb-0! text-[10px]! text-grey leading-relaxed!">arch</p>
            <strong class="ms-auto">{hoveredModelData.arch}</strong>
          </div>
          <div class="flex gap-1 leading-relaxed">
            <p class="mb-0! text-[10px]! text-grey leading-relaxed!">paramètres</p>
            <strong class="ms-auto">{hoveredModelData.params}</strong>
          </div>
          <div class="flex gap-1 leading-relaxed">
            <p class="mb-0! text-[10px]! text-grey leading-relaxed!">paramètres actifs</p>
            <strong class="ms-auto">{hoveredModelData.active_params ?? 'N/A'}</strong>
          </div>
        </div>
      </div>
    {/if}

    <div
      id="graph-legend"
      class="cg-border rounded-md! absolute max-w-[190px] border-dashed bg-white p-4 text-[12px] leading-normal"
    >
      <strong>{legend.legend}</strong>
      <ul class="p-0! list-none! font-medium">
        {#each legend.elems as elem}
          <li class="p-0! mb-2 flex items-center">
            <div class="me-2 min-h-4 min-w-4 rounded-full {elem.class}"></div>
            {elem.label}
          </li>
        {/each}
      </ul>
    </div>

    <div class="text-center">
      {#if dotMode === 'params'}
        <strong>Nombre de paramètres {useActiveParams ? 'actifs' : 'totaux'}</strong>
      {:else}
        <Icon icon="flashlight-line" class="text-primary" />
        <strong>{m['ranking.energy.views.graph.xLabel']()}</strong>
      {/if}
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

    .elo-median {
      stroke: var(--grey-625-425);
      stroke-dasharray: 5;
    }

    /* Dots color */
    .proprietary {
      fill: #cecece;
      background-color: #cecece;
    }
    .XS,
    .moe {
      fill: var(--green-emeraude-main-632);
      background-color: var(--green-emeraude-main-632);
    }
    .S,
    .dense {
      fill: var(--green-emeraude-850-200);
      background-color: var(--green-emeraude-850-200);
    }
    .M,
    .matformer {
      fill: var(--red-marianne-850-200);
      background-color: var(--red-marianne-850-200);
    }
    .L {
      fill: var(--orange-terre-battue-main-645);
      background-color: var(--orange-terre-battue-main-645);
    }
    .XL {
      fill: var(--red-marianne-main-472);
      background-color: var(--red-marianne-main-472);
    }
  }

  #graph-tooltip {
    top: var(--y);
    left: var(--x);
    transform: translate(-50%, calc(-100% - 0.75rem));
  }

  #graph-legend {
    right: 0px;
    bottom: 75px;
  }
</style>
