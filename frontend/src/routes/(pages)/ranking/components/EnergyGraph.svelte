<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { CheckboxGroup, Icon, Search, Toggle, Tooltip } from '$components/dsfr'
  import { ARCHS } from '$lib/generated/models'
  import { m } from '$lib/i18n/messages'
  import type { Archs, ConsoSizes, Sizes } from '$lib/models'
  import { CONSO_SIZES, getModelsContext, getModelsWithDataContext, SIZES } from '$lib/models'
  import { sortIfDefined } from '$lib/utils/data'
  import { extent, ticks } from 'd3-array'
  import { scaleLinear } from 'd3-scale'
  import { onMount } from 'svelte'

  let { useStyleControl = false }: { useStyleControl?: boolean } = $props()

  type ModelGraphData = (typeof models)[number]

  const modelsContext = getModelsWithDataContext()

  // Transform data based on style control toggle
  // When enabled, use style_controlled values (no trust_range filter for style-controlled)
  const data = $derived.by(() => {
    if (!useStyleControl) return modelsContext.models

    // For style control, start from ALL models and filter based on style_controlled criteria
    const allModels = getModelsContext().models

    const filtered = allModels.filter((model) => {
      if (!model.data?.style_controlled) return false
      if (!model.prefs) return false
      return true
    })

    return filtered.map((model) => {
      const sc = model.data!.style_controlled!

      return {
        ...model,
        data: {
          ...model.data,
          elo: sc.elo,
          rank: sc.rank,
          score_p2_5: sc.score_p2_5,
          score_p97_5: sc.score_p97_5,
          rank_p2_5: sc.rank_p2_5,
          rank_p97_5: sc.rank_p97_5,
          trust_range: sc.trust_range
        }
      }
    })
  })

  const dotSizes = { XS: 5, S: 7, M: 9, L: 11, XL: 13 } as const

  // Explicit dependency to ensure reactivity when style control toggles
  const models = $derived.by(() => {
    const _ = useStyleControl
    return data
      .filter((m) => m.license !== 'proprietary')
      .sort((a, b) => sortIfDefined(a, b, 'params'))
      .map((m) => {
        return {
          ...m,
          x: m.consumption_wh,
          y: m.data.elo,
          radius: dotSizes[m.friendly_size],
          class: m.license === 'proprietary' ? 'na' : m.arch,
          consoSize:
            m.consumption_wh < 10
              ? ('S' as const)
              : m.consumption_wh < 100
                ? ('M' as const)
                : ('L' as const)
        }
      })
  })

  let search = $state('')
  let sizes = $state<Sizes[]>([])
  let consos = $state<ConsoSizes[]>(['S', 'M'])
  let showArchived = $state(true)
  const sizeFilter = {
    id: 'size',
    legend: m['models.list.filters.size.legend'](),
    options: SIZES.map((value) => ({
      value,
      label: m[`models.size.count.${value}`]()
    }))
  }
  const consoFilter = {
    id: 'conso',
    legend: m['models.conso.filterLegend'](),
    options: CONSO_SIZES.map((value) => ({
      value,
      label: m[`models.conso.count.${value}`]()
    }))
  }

  const filteredModels = $derived.by(() => {
    const _search = search.toLowerCase()
    return models.filter((m) => {
      const sizeMatch = sizes.length === 0 || sizes.includes(m.friendly_size)
      const consoMatch = consos.length === 0 || consos.includes(m.consoSize)
      const searchMatch = !_search || m.search.includes(_search)
      const archivedMatch = m.status === 'enabled' || showArchived

      return sizeMatch && consoMatch && searchMatch && archivedMatch
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
  let height = $state(700)

  const padding = { top: 5, right: 10, bottom: 35, left: 72 }

  const minMaxX = $derived.by(() => {
    const [min, max] = extent(filteredModels, (m) => m.x) as [number, number]
    if (min === undefined || max === undefined) return [0, 100] as const
    return [min - 5, max + 15] as const
  })
  const minMaxY = $derived.by(() => {
    const [min, max] = extent(filteredModels, (m) => m.y) as [number, number]
    if (min === undefined || max === undefined) return [0, 1000] as const
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

{#snippet legend(kind: string)}
  <div
    id="graph-legend"
    class="cg-border rounded-md! bg-very-light-grey p-4 leading-normal flex h-full flex-col text-[12px]"
  >
    <Search
      id="energy-graph-model-search"
      bind:value={search}
      label={m['words.search']()}
      class="mb-5"
    />

    <p class="mb-1! leading-normal! text-[13px]!" aria-hidden="true">
      <strong>{consoFilter.legend}</strong>
    </p>
    <CheckboxGroup
      {...consoFilter}
      bind:value={consos}
      legendClass="sr-only"
      labelClass="text-dark-grey! text-[12px]! font-medium!"
      row
      class="mb-5!"
    ></CheckboxGroup>

    <p class="mb-1! leading-tight! text-[13px]!" aria-hidden="true">
      <strong>{m['ranking.energy.views.graph.legends.size']()}</strong><br />
      <span class="text-[11px]">{m['ranking.energy.views.graph.legends.sizeSub']()}</span>
    </p>

    <CheckboxGroup {...sizeFilter} bind:value={sizes} legendClass="sr-only" row class="mb-5!">
      {#snippet labelSlot({ option })}
        <div class="flex items-center">
          <div
            class={['dot border-dark-grey me-2 rounded-full border']}
            style="--size: {dotSizes[option.value] * 2}px"
          ></div>
          <span class="text-dark-grey font-medium text-[12px]">{option.label}</span>
        </div>
      {/snippet}
    </CheckboxGroup>

    <Toggle
      id="archived-{kind}"
      bind:value={showArchived}
      label={m['models.list.filters.archived.label']()}
      checkedLabel={m['models.list.filters.archived.checkedLabel']()}
      uncheckedLabel={m['models.list.filters.archived.uncheckedLabel']()}
      inline={false}
      groupClass="mb-2"
      class="mb-2! leading-tight! font-medium text-[13px]! text-[--text-default-grey]"
      checkLabelClass="text-[12px]"
    />

    <hr class="pb-2!" />
    <p class="mb-1! leading-normal! text-[13px]!">
      <strong>{m['ranking.energy.views.graph.legends.arch']()}</strong>
    </p>
    <ul class="mt-0! p-0! md:mb-10! gap-x-3 font-medium md:block flex list-none! flex-wrap">
      {#each ARCHS.filter((arch) => arch !== 'na') as arch (arch)}
        <li class="p-0! md:not-last:mb-2 flex items-center">
          <div class={['dot border-dark-grey me-2  rounded-full border', arch]}></div>
          {m[`generated.archs.${arch}.name`]()}
          <Tooltip
            id="arch-type-{arch}-{kind}"
            text={m[`generated.archs.${arch}.desc`]()}
            size="xs"
            class="ms-1"
          />
        </li>
      {/each}
    </ul>
  </div>
{/snippet}

<div id="energy-graph">
  <div class="gap-2 flex items-center">
    <div
      class="-me-8 h-6 w-6 translate-y-[35px] -rotate-90 overflow-visible text-center whitespace-nowrap"
    >
      <Icon icon="thumb-up-line" class="text-primary" />
      <strong>{m['ranking.energy.views.graph.yLabel']()}</strong>
    </div>

    <div class="relative flex-grow">
      <div class="flex">
        <svg bind:this={svg}>
          <!-- y axis -->
          <g class="axis y-axis">
            {#each yTicks as tick (tick)}
              <g transform="translate(0, {yScale(tick)})">
                <line x1={padding.left} x2={xScale(minMaxX[1])} />
                <text x={padding.left - 8} y="+4">{tick}</text>
              </g>
            {/each}
          </g>

          <!-- x axis -->
          <g class="axis x-axis">
            {#each xTicks as tick (tick)}
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
              <text x={padding.left - 32} y="+4">{hoveredModelData.y} BT</text>
            </g>

            <!-- x axis -->
            <g class="target-line" transform="translate({xScale(hoveredModelData.x)},0)">
              <line y1={yScale(minMaxY[0])} y2={yScale(hoveredModelData.y)} />
              <rect y={height - padding.bottom} x="-35" width="70" height="30" rx="4" ry="4" />
              <text y={height - padding.bottom + 20}>{hoveredModelData.x} WH</text>
            </g>
          {/if}

          <!-- data -->
          {#each filteredModels as m (m.id)}
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
            class="cg-border rounded-sm! bg-white p-3 drop-shadow-md absolute z-1 min-w-[175px]"
            style="--x: {tooltipPos.x}px; --y:{tooltipPos.y}px;"
          >
            <div class="flex">
              <AILogo
                iconPath={hoveredModelData.icon_path}
                alt={hoveredModelData.organisation}
                class="me-1"
              />
              <strong class="leading-normal text-[14px]">{hoveredModelData.id}</strong>
            </div>

            <div class="mt-1 text-[12px]">
              {#each [{ key: 'elo', icon: 'thumb-up-line' }, { key: 'consumption_wh', icon: 'i-ri-flashlight-line' }] as const as item (item.key)}
                <div class="gap-1 leading-relaxed flex">
                  <Icon icon={item.icon} size="xxs" class="text-primary" />
                  <p class="mb-0! leading-relaxed! text-grey text-[12px]!">
                    {m[`ranking.energy.views.graph.tooltip.${item.key}`]()}
                  </p>
                  <strong class="ms-auto"
                    >{item.key === 'elo'
                      ? hoveredModelData.data[item.key]
                      : hoveredModelData[item.key]}</strong
                  >
                </div>
              {/each}

              <div class="mt-4">
                {#each tooltipExtraData as key (key)}
                  {#if hoveredModelData[key]}
                    <div class="gap-1 leading-relaxed flex">
                      <p class="mb-0! leading-relaxed! text-grey text-[12px]!">
                        {m[`ranking.energy.views.graph.tooltip.${key}`]()}
                      </p>
                      <strong class="ms-auto">
                        {#if key === 'arch'}
                          {m[
                            `generated.archs.${hoveredModelData.license === 'proprietary' ? 'na' : (hoveredModelData.arch as Archs)}.name`
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

        <div class="md:block hidden h-[675px] w-[230px]">
          {@render legend('desktop')}
        </div>
      </div>

      <div class="text-center">
        <Icon icon="i-ri-flashlight-line" class="text-primary" />
        <strong>{m['ranking.energy.views.graph.xLabel']()}</strong>
      </div>
    </div>
  </div>

  <div class="mt-6 md:hidden">
    {@render legend('mobile')}
  </div>
</div>

<style lang="postcss">
  #energy-graph {
    svg {
      width: 100%;
      height: 700px;
    }

    text {
      fill: var(--grey-0-1000);
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
        stroke: var(--grey-425-625);
        stroke-dasharray: 5;
        stroke-width: 2px;
      }

      rect {
        fill: var(--grey-0-1000);
      }

      text {
        text-anchor: middle;
        font-size: 14px;
        fill: var(--grey-1000-50);
        font-weight: 700;
      }
    }

    circle {
      stroke-width: 1px;
      stroke: var(--grey-200-850);

      &.hovered {
        stroke: var(--grey-200-850);
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
      fill: var(--green-archipel-925-125);
      background-color: var(--green-archipel-925-125);
    }
    .dense {
      fill: var(--cg-orange);
      background-color: var(--cg-orange);
    }
    .matformer {
      fill: var(--blue-france-main-525);
      background-color: var(--blue-france-main-525);
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
      width: var(--size, 16px);
      height: var(--size, 16px);
    }
  }
</style>
