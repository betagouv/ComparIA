<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { CheckboxGroup, Icon, Search, Toggle } from '$components/dsfr'
  import GraphDot from './GraphDot.svelte'
  import { convertFromUsd, formatCurrencyFromUsd } from '$lib/currency'
  import type { APILLMData } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { applyStyleControl, getModelsWithDataContext } from '$lib/models'
  import { paretoFrontier } from '$lib/pareto'
  import { extent } from 'd3-array'
  import { scaleLinear, scaleLog } from 'd3-scale'
  import { onMount } from 'svelte'

  type LicenseKind = APILLMData['license']['kind']
  type ModelGraphData = (typeof models)[number]

  const LICENSE_KINDS = ['open-source', 'open-weights', 'proprietary'] as const

  const { models: baseModels, commons } = getModelsWithDataContext()
  const data = $derived(applyStyleControl(baseModels))
  const locale = getLocale()

  // A log axis has no place for a free model. None is priced at zero today;
  // the guard keeps the scale finite if one ever is.
  const models = $derived(
    data
      .filter((llm) => llm.price_out > 0)
      .map((llm) => ({
        ...llm,
        x: convertFromUsd(llm.price_out, commons.currency),
        y: llm.data.elo
      }))
  )

  let search = $state('')
  let kinds = $state<LicenseKind[]>([])
  let frontierOnly = $state(false)
  let showArchived = $state(true)
  const kindFilter = {
    id: 'license-kind',
    legend: m['ranking.price.views.graph.legends.license'](),
    options: LICENSE_KINDS.map((value) => ({
      value,
      label: m[`ranking.price.views.graph.legends.kinds.${value}`]()
    }))
  }

  // The frontier is drawn over the whole set of models on screen except the
  // "frontier only" switch, which hides the rest rather than moving the line.
  const candidates = $derived.by(() => {
    const _search = search.toLowerCase()
    return models.filter((llm) => {
      const kindMatch = kinds.length === 0 || kinds.includes(llm.license.kind)
      const searchMatch = !_search || llm.search.includes(_search)
      const archivedMatch = llm.status === 'enabled' || showArchived

      return kindMatch && searchMatch && archivedMatch
    })
  })
  const frontierIds = $derived(new Set(paretoFrontier(candidates)))
  const frontierModels = $derived(
    candidates.filter((llm) => frontierIds.has(llm.id)).sort((a, b) => a.x - b.x)
  )
  const filteredModels = $derived(frontierOnly ? frontierModels : candidates)

  let hoveredModel = $state<string>()
  let tooltipPos = $state({ x: 0, y: 0 })
  const hoveredModelData = $derived(filteredModels.find((llm) => llm.id === hoveredModel))

  let svg = $state<SVGSVGElement>()
  let width = $state(1100)
  let height = $state(700)

  const padding = { top: 5, right: 10, bottom: 35, left: 72 }
  const dotRadius = 11

  const minMaxX = $derived.by(() => {
    const [min, max] = extent(filteredModels, (llm) => llm.x) as [number, number]
    return [min * 0.7, max * 1.5] as const
  })
  const minMaxY = $derived.by(() => {
    const [min, max] = extent(filteredModels, (llm) => llm.y) as [number, number]
    return [min - 5, max + 35] as const
  })
  // Price runs right to left: the dearest models sit on the left, the
  // cheapest on the right, so the frontier reads as a descent from the best
  // model to the cheapest and the top-right corner is the one to aim for.
  const xScale = $derived(scaleLog(minMaxX, [width - padding.right, padding.left]))
  const yScale = $derived(scaleLinear(minMaxY, [height - padding.bottom, padding.top]))
  // d3's log ticks fill every decade; keep the round ones so labels stay apart.
  const xTicks = $derived(
    xScale.ticks().filter((tick) => {
      const mantissa = tick / 10 ** Math.floor(Math.log10(tick))
      return (
        Math.abs(mantissa - Math.round(mantissa)) < 1e-9 && [1, 2, 5].includes(Math.round(mantissa))
      )
    })
  )
  const yTicks = $derived(yScale.ticks(9))

  const tickFormat = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: commons.currency.code,
    currencyDisplay: 'narrowSymbol',
    maximumSignificantDigits: 2
  })
  const price = (usd: number) => formatCurrencyFromUsd(usd, commons.currency, locale)

  // Flat runs to both edges: nothing cheaper beats the cheapest frontier
  // model, nothing pricier beats the best one.
  const frontierPath = $derived.by(() => {
    if (frontierModels.length === 0) return ''
    const first = frontierModels[0]
    const last = frontierModels[frontierModels.length - 1]
    return [
      `${xScale(minMaxX[0])},${yScale(first.y)}`,
      ...frontierModels.map((llm) => `${xScale(llm.x)},${yScale(llm.y)}`),
      `${xScale(minMaxX[1])},${yScale(last.y)}`
    ].join(' ')
  })
  const showLabels = $derived(width >= 640)

  onMount(() => {
    const resizeObserver = new ResizeObserver(([entry]) => {
      if (!entry) return

      const { width: nextWidth, height: nextHeight } = entry.contentRect
      if (nextWidth === 0 || nextHeight === 0) return

      width = nextWidth
      height = nextHeight
    })

    resizeObserver.observe(svg!)
    return () => resizeObserver.disconnect()
  })

  function onModelHover(model: ModelGraphData) {
    hoveredModel = model.id
    tooltipPos = { x: xScale(model.x), y: yScale(model.y) }
  }
</script>

{#snippet legend(kind: string)}
  <div
    class="graph-legend cg-border rounded-md! bg-very-light-grey p-4 leading-normal flex h-full flex-col text-[12px]"
  >
    <Search
      id="price-graph-model-search-{kind}"
      bind:value={search}
      label={m['words.search']()}
      class="mb-5"
    />

    <p class="mb-1! leading-normal! text-[13px]!" aria-hidden="true">
      <strong>{kindFilter.legend}</strong>
    </p>
    <CheckboxGroup
      {...kindFilter}
      id="{kindFilter.id}-{kind}"
      bind:value={kinds}
      legendClass="sr-only"
      class="mb-5!"
    >
      {#snippet labelSlot({ option })}
        <div class="flex items-center">
          <div class={['dot border-dark-grey me-2 rounded-full border', option.value]}></div>
          <span class="text-dark-grey font-medium text-[12px]">{option.label}</span>
        </div>
      {/snippet}
    </CheckboxGroup>

    <Toggle
      id="frontier-only-{kind}"
      bind:value={frontierOnly}
      label={m['ranking.price.views.graph.legends.frontierOnly']()}
      hideCheckLabel
      inline={false}
      groupClass="mb-2"
      class="mb-2! leading-tight! font-medium text-[13px]! text-[--text-default-grey]"
    />

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
    <p class="mb-1! leading-normal! flex items-center text-[13px]!">
      <span class="frontier-swatch me-2 w-6 inline-block h-[3px] rounded-full"></span>
      <strong>{m['ranking.price.views.graph.legends.frontier']()}</strong>
    </p>
    <p class="mb-0! text-grey text-[11px]">
      {m['ranking.price.views.graph.legends.frontierSub']()}
    </p>
  </div>
{/snippet}

<div id="price-graph">
  <div class="gap-2 flex items-center">
    <div
      class="-me-8 h-6 w-6 translate-y-[35px] -rotate-90 overflow-visible text-center whitespace-nowrap"
    >
      <Icon icon="thumb-up-line" class="text-primary" />
      <strong>{m['ranking.price.views.graph.yLabel']()}</strong>
    </div>

    <div class="relative flex-grow">
      <div class="flex">
        <!-- Named and described here; the same figures sit in #price-table
             below, which is the version a screen reader can read. -->
        <svg
          bind:this={svg}
          role="img"
          aria-labelledby="price-graph-title"
          aria-describedby="price-graph-desc"
        >
          <title id="price-graph-title">{m['ranking.price.views.graph.title']()}</title>
          <desc id="price-graph-desc">{m['a11y.priceGraphDesc']()}</desc>
          <!-- y axis -->
          <g class="axis y-axis">
            {#each yTicks as tick (tick)}
              <g transform="translate(0, {yScale(tick)})">
                <line x1={padding.left} x2={width - padding.right} />
                <text x={padding.left - 8} y="+4">{tick}</text>
              </g>
            {/each}
          </g>

          <!-- x axis -->
          <g class="axis x-axis">
            {#each xTicks as tick (tick)}
              <g transform="translate({xScale(tick)},0)">
                <line y1={yScale(minMaxY[0])} y2={yScale(minMaxY[1])} />
                <text y={height - padding.bottom + 20}>{tickFormat.format(tick)}</text>
              </g>
            {/each}
          </g>

          <!-- target lines -->
          {#if hoveredModelData}
            <g class="target-line" transform="translate(0, {yScale(hoveredModelData.y)})">
              <line x1={padding.left} x2={xScale(hoveredModelData.x)} />
              <rect y="-15" x={padding.left - 72} width="78" height="30" rx="4" ry="4" />
              <text x={padding.left - 32} y="+4">{hoveredModelData.y} BT</text>
            </g>

            <g class="target-line" transform="translate({xScale(hoveredModelData.x)},0)">
              <line y1={yScale(minMaxY[0])} y2={yScale(hoveredModelData.y)} />
              <rect y={height - padding.bottom} x="-45" width="90" height="30" rx="4" ry="4" />
              <text y={height - padding.bottom + 20}>{tickFormat.format(hoveredModelData.x)}</text>
            </g>
          {/if}

          <!-- frontier -->
          {#if frontierModels.length > 0}
            <polyline class="frontier" points={frontierPath} />
          {/if}

          <!-- data -->
          {#each filteredModels as llm (llm.id)}
            {@const onFrontier = frontierIds.has(llm.id)}
            <GraphDot
              cx={xScale(llm.x)}
              cy={yScale(llm.y)}
              r={onFrontier ? dotRadius + 2 : dotRadius}
              model={llm}
              class={[
                llm.license.kind,
                {
                  frontier: onFrontier,
                  hovered: hoveredModel === llm.id,
                  blurred: hoveredModel && hoveredModel !== llm.id
                }
              ]}
              onpointerenter={() => onModelHover(llm)}
              onpointerleave={() => (hoveredModel = undefined)}
            />
          {/each}

          <!-- frontier labels, flipped to the left of the dot when they
               would run off the chart -->
          {#if showLabels && !hoveredModel}
            {#each frontierModels as llm (llm.id)}
              {@const flip = xScale(llm.x) + dotRadius + 6 + llm.human_id.length * 7 > width}
              <text
                class="label"
                x={xScale(llm.x) + (flip ? -1 : 1) * (dotRadius + 6)}
                y={yScale(llm.y) - dotRadius - 4}
                text-anchor={flip ? 'end' : 'start'}
                aria-hidden="true">{llm.human_id}</text
              >
            {/each}
          {/if}
        </svg>

        {#if hoveredModelData}
          <div
            class="graph-tooltip cg-border rounded-sm! bg-white p-3 drop-shadow-md absolute z-1 min-w-[175px]"
            style="--x: {tooltipPos.x}px; --y:{tooltipPos.y}px;"
          >
            <div class="flex">
              <AILogo
                logo={hoveredModelData.lab.logo}
                customLogoId={hoveredModelData.lab.has_custom_logo
                  ? hoveredModelData.lab.id
                  : undefined}
                alt={hoveredModelData.lab.name}
                class="me-1"
              />
              <strong class="leading-normal text-[14px]">{hoveredModelData.human_id}</strong>
            </div>

            <div class="mt-1 text-[12px]">
              {#each [{ key: 'elo', icon: 'thumb-up-line', value: String(hoveredModelData.data.elo) }, { key: 'price_out', icon: 'i-ri-money-euro-circle-line', value: price(hoveredModelData.price_out) }, { key: 'price_in', icon: 'i-ri-money-euro-circle-line', value: price(hoveredModelData.price_in) }] as const as item (item.key)}
                <div class="gap-1 leading-relaxed flex">
                  <Icon icon={item.icon} size="xxs" class="text-primary" />
                  <p class="mb-0! leading-relaxed! text-grey text-[12px]!">
                    {m[`ranking.price.views.graph.tooltip.${item.key}`]()}
                  </p>
                  <strong class="ms-auto">{item.value}</strong>
                </div>
              {/each}

              <div class="mt-4 gap-1 leading-relaxed flex">
                <p class="mb-0! leading-relaxed! text-grey text-[12px]!">
                  {m['ranking.price.views.graph.tooltip.license']()}
                </p>
                <strong class="ms-auto">{hoveredModelData.badges.license.text}</strong>
              </div>
              {#if frontierIds.has(hoveredModelData.id)}
                <p class="mt-2 mb-0! frontier-text font-medium text-[12px]!">
                  {m['ranking.price.views.graph.tooltip.onFrontier']()}
                </p>
              {/if}
            </div>
          </div>
        {/if}

        <div class="md:block hidden h-[675px] w-[230px]">
          {@render legend('desktop')}
        </div>
      </div>

      <div class="text-center">
        <Icon icon="i-ri-money-euro-circle-line" class="text-primary" />
        <strong>{m['ranking.price.views.graph.xLabel']({ currency: commons.currency.code })}</strong
        >
      </div>
    </div>
  </div>

  <div class="mt-6 md:hidden">
    {@render legend('mobile')}
  </div>
</div>

<style lang="postcss">
  #price-graph {
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

    .frontier {
      fill: none;
      stroke: var(--brand-primary);
      stroke-width: 2.5px;
      stroke-linejoin: round;
    }

    .label {
      font-size: 12px;
      font-weight: 700;
      paint-order: stroke;
      stroke: var(--grey-1000-50);
      stroke-width: 3px;
      stroke-linejoin: round;
      pointer-events: none;
    }

    /* Dots live in GraphDot, hence the :global hooks. A ring in the licence
       colour around the lab mark; the frontier's ring is thicker and green so
       the line runs through matching dots. */
    svg :global(circle) {
      fill: var(--background-default-grey);
      stroke-width: 2px;
    }
    svg :global(circle.frontier) {
      stroke: var(--brand-primary);
      stroke-width: 3px;
    }

    svg :global(circle),
    svg :global(foreignObject) {
      opacity: 0.55;
      transition: opacity 0.15s;
    }
    svg :global(circle.frontier),
    svg :global(circle.frontier + foreignObject),
    svg :global(circle.hovered),
    svg :global(circle.hovered + foreignObject) {
      opacity: 1;
    }
    svg :global(circle.blurred),
    svg :global(circle.blurred + foreignObject) {
      opacity: 0.25;
    }

    .frontier-swatch {
      background-color: var(--brand-primary);
    }

    .frontier-text {
      color: var(--brand-primary);
    }

    /* Dots color, same ramp as the licence badges */
    :global(.open-source) {
      stroke: var(--cg-green);
      border-color: var(--cg-green);
    }
    :global(.open-weights) {
      stroke: var(--yellow-tournesol-main-731);
      border-color: var(--yellow-tournesol-main-731);
    }
    :global(.proprietary) {
      stroke: var(--cg-orange);
      border-color: var(--cg-orange);
    }
  }

  .graph-tooltip {
    top: var(--y);
    left: var(--x);

    transform: translate(-50%, calc(-100% - 1.5rem));

    @media (min-width: 36em) {
      transform: translate(1.5rem, calc(-1.5rem));
    }
  }

  .graph-legend {
    /* Rings, like the dots on the chart. */
    .dot {
      width: 14px;
      height: 14px;
      border-width: 3px;
    }
  }
</style>
