<script lang="ts">
  import { extent, range, scaleLinear, ticks } from 'd3'
  import { onMount } from 'svelte'

  let { data, minMaxY }: { data: { x: string; y: number }[]; minMaxY: [number, number] } = $props()

  let svg = $state<SVGSVGElement>()
  let width = $state(528)
  let height = $state(400)

  const padding = { top: 20, bottom: 130, left: 50, right: 20 }

  let minMaxX = $derived(extent(range(11)) as [number, number])
  let xScale = $derived(scaleLinear(minMaxX, [padding.left, width - padding.right]))
  let yScale = $derived(scaleLinear(minMaxY, [height - padding.bottom, padding.top]))
  const xTicks = $derived(ticks(0, 9, 10))
  const yTicks = $derived(ticks(...minMaxY, 6))

  onMount(resize)

  function resize() {
    ;({ width, height } = svg!.getBoundingClientRect())
  }

  const barWidth = $derived(xScale(1) - xScale(0))
</script>

<svg bind:this={svg} class="histogram">
  <g>
    <!-- bars -->
    {#each data as d, i}
      <rect
        x={xScale(i)}
        y={yScale(d.y)}
        width={barWidth}
        height={height - padding.bottom - yScale(d.y)}
        class="fill-primary stroke-white"
      />
    {/each}
  </g>

  <!-- y axis -->
  <g transform="translate({padding.left}, 0)">
    {#each yTicks as y}
      <g class="axis" transform="translate(0,{yScale(y)})">
        <line x2="-5" />
        <text x="-10" y="+4">
          {(y * 100).toFixed()}%
        </text>
      </g>
    {/each}
  </g>

  <!-- x axis -->
  <g transform="translate(0, {height - padding.bottom})">
    {#each xTicks as x, i}
      <g class="axis" transform="translate({xScale(x)},0)">
        <!-- <line y2="6" /> -->
        <text x={barWidth / 2} class="rotated">
          {data[i].x}
        </text>
      </g>
    {/each}
  </g>
</svg>

<style lang="postcss">
  .histogram {
    width: 100%;
    height: 100%;

    text {
      font-size: 12px;
      text-anchor: end;
      fill: var(--color-black);

      &.rotated {
        transform: rotate(-65deg) translate(-20px, 30px);
      }
    }

    line {
      stroke: var(--color-black);
    }
  }
</style>
