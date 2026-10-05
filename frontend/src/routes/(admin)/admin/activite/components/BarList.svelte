<script lang="ts">
  import { getLocale } from '$lib/i18n/runtime'

  export type Bar = { key: string; label: string; count: number }

  let { id, title, bars }: { id: string; title: string; bars: Bar[] } = $props()

  const numberFormatter = new Intl.NumberFormat(getLocale())
  const percentFormatter = new Intl.NumberFormat(getLocale(), {
    style: 'percent',
    maximumFractionDigits: 1
  })
  const sorted = $derived([...bars].sort((a, b) => b.count - a.count))
  const max = $derived(Math.max(1, ...bars.map((bar) => bar.count)))
  const total = $derived(bars.reduce((sum, bar) => sum + bar.count, 0))
</script>

<figure {id} class="m-0!">
  <figcaption class="text-base font-bold mb-2!">{title}</figcaption>
  <dl class="gap-2 m-0! flex flex-col">
    {#each sorted as bar (bar.key)}
      <div>
        <div class="gap-3 text-sm flex items-baseline">
          <dt class="min-w-0 flex-1">{bar.label}</dt>
          <dd class="m-0! tabular-nums">
            <strong>{numberFormatter.format(bar.count)}</strong>
            <span class="text-[--text-mention-grey]">
              {percentFormatter.format(total ? bar.count / total : 0)}
            </span>
          </dd>
        </div>
        <dd class="bar-track" aria-hidden="true">
          <div class="bar" style:width="{(bar.count / max) * 100}%"></div>
        </dd>
      </div>
    {/each}
  </dl>
</figure>

<style>
  /* One hue, longest first: the bars only compare sizes. Square at the
     baseline, rounded at the value end. */
  .bar-track {
    margin: 0.25rem 0 0;
    height: 0.5rem;
  }
  .bar {
    height: 100%;
    min-width: 2px;
    border-radius: 0 4px 4px 0;
    background: var(--brand-primary);
  }
</style>
