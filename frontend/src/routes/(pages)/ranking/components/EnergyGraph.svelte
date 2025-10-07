<script lang="ts">
  import { CheckboxGroup, Icon, Search, Tooltip } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import type { BotModel, Sizes } from '$lib/models'
  import { SIZES } from '$lib/models'
  import { sortIfDefined } from '$lib/utils/data'
  import { extent, ticks } from 'd3-array'
  import { scaleLinear } from 'd3-scale'
  import { onMount } from 'svelte'

  type ModelGraphData = (typeof models)[number]

  let { data }: { data: BotModel[] } = $props()

  const dotSizes = { XS: 3, S: 5, M: 7, L: 9, XL: 11 } as const
  const archs = ['moe', 'dense', 'matformer', 'na'] as const

  const models = $derived(
    data
      .sort((a, b) => sortIfDefined(a, b, 'params'))
      .map((m) => {
        return {
          ...m,
          x: m.consumption_wh!,
          y: m.elo!,
          radius: dotSizes[m.friendly_size],
          class: m.license === 'proprietary' ? 'na' : m.arch,
          search: (['id', 'simple_name', 'organisation'] as const)
            .map((key) => m[key].toLowerCase())
            .join(' ')
        }
      })
  )

  let search = $state('')
  let sizes = $state<Sizes[]>([])
  const sizeFilter = {
    id: 'size',
    legend: m['models.list.filters.size.legend'](),
    options: SIZES.map((value) => ({
      value,
      label: m[`models.size.count.${value}`]()
    }))
  }

  const filteredModels = $derived.by(() => {
    const _search = search.toLowerCase()
    return models.filter((m) => {
      const sizeMatch = sizes.length === 0 || sizes.includes(m.friendly_size)
      const searchMatch = !_search || m.search.includes(_search)
      return sizeMatch && searchMatch
    })
  })

  let hoveredModel = $state<string>()
  let tooltipPos = $state({ x: 0, y: 0 })
  const hoveredModelData = $derived(filteredModels.find((m) => m.id === hoveredModel))
  const tooltipExtraData = $derived(
    hoveredModelData?.license === 'proprietary'
      ? (['arch'] as const)
      : (['arch', 'params', 'active_params'] as const)
  )

  let svg = $state<SVGSVGElement>()
  let width = $state(1100)
  let height = $state(570)

  const padding = { top: 5, right: 10, bottom: 35, left: 72 }

  const minMaxX = $derived.by(() => {
    const [min, max] = extent(filteredModels, (m) => m.x) as [number, number]
    return [min - 5, max + 15] as const
  })
  const minMaxY = $derived.by(() => {
    const [min, max] = extent(filteredModels, (m) => m.y) as [number, number]
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

<div class="mb-4 flex">
  <Search
    id="energy-graph-model-search"
    bind:value={search}
    label={m['ranking.table.search']()}
    class="ms-auto"
  />
</div>

<div id="energy-graph" class="flex items-center gap-2">
  <div
    class="-me-8 h-6 w-6 translate-y-[95px] -rotate-90 overflow-visible whitespace-nowrap text-center"
  >
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

        <!-- target lines -->
        {#if hoveredModelData}
          <!-- y axis -->
          <g class="target-line" transform="translate(0, {yScale(hoveredModelData.y)})">
            <line x1={padding.left} x2={xScale(hoveredModelData.x)} />
            <rect y="-15" x={padding.left - 72} width="78" height="30" rx="4" ry="4" />
            <text x={padding.left - 32} y="+4">{hoveredModelData.y} ELO</text>
          </g>

          <!-- x axis -->
          <g class="target-line" transform="translate({xScale(hoveredModelData.x)},0)">
            <line y1={yScale(minMaxY[0])} y2={yScale(hoveredModelData.y)} />
            <rect y={height - padding.bottom} x="-35" width="70" height="30" rx="4" ry="4" />
            <text y={height - padding.bottom + 20}>{hoveredModelData.x} WH</text>
          </g>
        {/if}

        <!-- data -->
        {#each filteredModels as m}
          <circle
            cx={xScale(m.x)}
            cy={yScale(m.y)}
            r={m.radius}
            class={[
              m.class,
              { hovered: hoveredModel === m.id, blurred: hoveredModel && hoveredModel !== m.id }
            ]}
            onpointerenter={() => onModelHover(m)}
            onpointerleave={() => (hoveredModel = undefined)}
          />
        {/each}
      </svg>

      {#if hoveredModelData}
        <div
          id="graph-tooltip"
          class="cg-border rounded-sm! z-1 absolute min-w-[175px] bg-white p-3 drop-shadow-md"
          style="--x: {tooltipPos.x}px; --y:{tooltipPos.y}px;"
        >
          <div class="flex">
            <img
              src="/orgs/ai/{hoveredModelData.icon_path}"
              alt={hoveredModelData.organisation}
              class="me-1 w-[14px] object-contain"
            />
            <strong class="text-[12px] leading-normal">{hoveredModelData.id}</strong>
          </div>

          <div class="mt-1 text-[10px]">
            {#each [{ key: 'elo', icon: 'thumb-up-line' }, { key: 'consumption_wh', icon: 'flashlight-line' }] as const as item}
              <div class="flex gap-1 leading-relaxed">
                <Icon icon={item.icon} size="xxs" class="text-primary" />
                <p class="mb-0! text-[10px]! text-grey leading-relaxed!">
                  {m[`ranking.energy.views.graph.tooltip.${item.key}`]()}
                </p>
                <strong class="ms-auto">{hoveredModelData[item.key]}</strong>
              </div>
            {/each}

            <div class="mt-4">
              {#each tooltipExtraData as key}
                {#if hoveredModelData[key]}
                  <div class="flex gap-1 leading-relaxed">
                    <p class="mb-0! text-[10px]! text-grey leading-relaxed!">
                      {m[`ranking.energy.views.graph.tooltip.${key}`]()}
                    </p>
                    <strong class="ms-auto">
                      {#if key === 'arch'}
                        {m[
                          `models.arch.types.${hoveredModelData.license === 'proprietary' ? 'na' : (hoveredModelData.arch as (typeof archs)[number])}.name`
                        ]()}
                      {:else}
                        {hoveredModelData[key]}
                      {/if}
                    </strong>
                  </div>
                {/if}
              {/each}
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
            <li class="p-0! mb-2 flex items-center">
              <div class={['dot me-2 rounded-full', arch]}></div>
              {m[`models.arch.types.${arch}.name`]()}
              <Tooltip
                id="arch-type-{arch}"
                text={m[`models.arch.types.${arch}.desc`]()}
                size="xs"
                class="ms-1"
              />
            </li>
          {/each}
        </ul>

        <p class="mb-4! text-[13px]! leading-tight!">
          <strong>{m['ranking.energy.views.graph.legends.size']()}</strong><br />
          <span class="text-[11px]">{m['ranking.energy.views.graph.legends.sizeSub']()}</span>
        </p>

        <CheckboxGroup
          {...sizeFilter}
          bind:value={sizes}
          legendClass="sr-only"
          labelClass="flex-nowrap!"
          class="mb-0!"
        >
          {#snippet labelSlot({ option })}
            <div
              class={['dot border-dark-grey me-2 rounded-full border']}
              style="--size: {dotSizes[option.value] * 2}px"
            ></div>
            <span class="text-dark-grey text-[12px] font-medium">{option.label}</span>
          {/snippet}
        </CheckboxGroup>
      </div>
    </div>

    <div class="text-center">
      <Icon icon="flashlight-line" class="text-primary" />
      <strong>{m['ranking.energy.views.graph.xLabel']()}</strong>
    </div>
  </div>
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

    .target-line {
      line {
        stroke: var(--color-grey);
        stroke-dasharray: 5;
        stroke-width: 2px;
      }

      text {
        text-anchor: middle;
        font-size: 14px;
        fill: var(--color-white);
        font-weight: 700;
      }
    }

    circle {
      &.hovered {
        stroke: var(--color-dark-grey);
        stroke-width: 2px;
      }

      &.blurred {
        opacity: 0.5;
      }
    }

    /* Dots color */
    .na {
      fill: #cecece;
      background-color: #cecece;
    }
    .moe {
      fill: var(--blue-france-main-525);
      background-color: var(--blue-france-main-525);
    }
    .dense {
      fill: var(--cg-orange);
      background-color: var(--cg-orange);
    }
    .matformer {
      fill: var(--green-menthe-850-200);
      background-color: var(--green-menthe-850-200);
    }
  }

  #graph-tooltip {
    top: var(--y);
    left: var(--x);

    transform: translate(-50%, calc(-100% - 1.5rem));

    @media (min-width: 36em) {
      transform: translate(1.5rem, calc(-1.5rem));
    }
  }

  #graph-legend {
    .dot {
      min-width: var(--size, 16px);
      min-height: var(--size, 16px);
    }
  }
</style>
