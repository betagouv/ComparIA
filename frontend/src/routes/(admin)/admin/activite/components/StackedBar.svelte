<script lang="ts">
  import { getLocale } from '$lib/i18n/runtime'

  export type Segment = { key: string; label: string; count: number; color: string }

  let { id, title, segments }: { id: string; title: string; segments: Segment[] } = $props()

  const numberFormatter = new Intl.NumberFormat(getLocale())
  const percentFormatter = new Intl.NumberFormat(getLocale(), {
    style: 'percent',
    maximumFractionDigits: 1
  })
  const total = $derived(segments.reduce((sum, segment) => sum + segment.count, 0))
  const share = (count: number) => (total ? count / total : 0)
</script>

<figure {id} class="m-0!">
  <figcaption class="text-base font-bold mb-2!">{title}</figcaption>
  <!-- Parts of a whole: one bar, a 2px gap between parts. The legend under it
       carries every label and number, so no part depends on its colour. -->
  <div class="stacked-bar" aria-hidden="true">
    {#each segments.filter((segment) => segment.count > 0) as segment (segment.key)}
      <div
        class="segment"
        style:flex-grow={segment.count}
        style:background={segment.color}
        title="{segment.label} : {numberFormatter.format(segment.count)} ({percentFormatter.format(
          share(segment.count)
        )})"
      ></div>
    {/each}
  </div>
  <dl class="legend">
    {#each segments as segment (segment.key)}
      <div class="legend-row">
        <dt class="gap-2 flex items-center">
          <span class="swatch" style:background={segment.color}></span>
          {segment.label}
        </dt>
        <dd class="value">{numberFormatter.format(segment.count)}</dd>
        <dd class="percent">{percentFormatter.format(share(segment.count))}</dd>
      </div>
    {/each}
  </dl>
</figure>

<style>
  .stacked-bar {
    display: flex;
    gap: 2px;
    height: 1rem;
    border-radius: 4px;
    overflow: hidden;
    background: var(--background-default-grey);
  }
  .segment {
    flex-basis: 0;
    min-width: 2px;
  }
  .legend {
    display: grid;
    grid-template-columns: 1fr auto auto;
    column-gap: 1rem;
    row-gap: 0.125rem;
    margin: 0.625rem 0 0;
    font-size: 0.875rem;
  }
  .legend-row {
    display: contents;
  }
  .swatch {
    width: 0.75rem;
    height: 0.75rem;
    border-radius: 2px;
    flex-shrink: 0;
  }
  .value,
  .percent {
    margin: 0;
    text-align: end;
    font-variant-numeric: tabular-nums;
  }
  .percent {
    color: var(--text-mention-grey);
  }
</style>
