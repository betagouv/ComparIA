<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'

  export type Step = {
    key: string
    label: string
    count: number
    // The conversation list narrowed to this step, and to those who stopped
    // just before it.
    href: string
    droppedHref?: string
  }

  let { id, title, steps }: { id: string; title: string; steps: Step[] } = $props()

  const numberFormatter = new Intl.NumberFormat(getLocale())
  const percentFormatter = new Intl.NumberFormat(getLocale(), {
    style: 'percent',
    maximumFractionDigits: 0
  })

  const top = $derived(Math.max(steps[0]?.count ?? 0, 1))
  // Never thinner than a sliver, so a step with a handful of conversations
  // still shows where it sits.
  const width = (count: number) => Math.max((count / top) * 100, 2)
  // The band joining two bars, as a trapezoid on the full track width.
  const band = (from: number, to: number) => {
    const a = width(from)
    const b = width(to)
    return `polygon(${50 - a / 2}% 0, ${50 + a / 2}% 0, ${50 + b / 2}% 100%, ${50 - b / 2}% 100%)`
  }
</script>

<section {id} aria-labelledby="{id}-title">
  <h2 id="{id}-title" class="text-base font-bold mb-2!">{title}</h2>
  <ol class="funnel">
    {#each steps as step, index (step.key)}
      {@const previous = index > 0 ? steps[index - 1] : null}
      {#if previous}
        <li class="funnel-gap" aria-hidden="true">
          <span></span>
          <div class="h-12 relative">
            <div
              class="inset-0 absolute bg-[--blue-france-975-75]"
              style:clip-path={band(previous.count, step.count)}
            ></div>
            <p class="fr-text--xs inset-0 mb-0! absolute flex items-center justify-center">
              <span class="px-2 py-0.5 font-bold rounded-full bg-[--background-default-grey]">
                {m['admin.activity.overview.funnel.continue']({
                  share: percentFormatter.format(previous.count ? step.count / previous.count : 0)
                })}
              </span>
            </p>
          </div>
          {#if step.droppedHref}
            <!-- eslint-disable svelte/no-navigation-without-resolve -- resolved by the caller -->
            <a
              href={step.droppedHref}
              class="fr-text--xs mb-0! justify-self-start text-[--text-mention-grey]"
            >
              {m['admin.activity.overview.funnel.dropped']({
                count: numberFormatter.format(previous.count - step.count)
              })}
            </a>
            <!-- eslint-enable svelte/no-navigation-without-resolve -->
          {:else}
            <span></span>
          {/if}
        </li>
      {/if}
      <li class="funnel-step">
        <!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- resolved by the caller -->
        <a href={step.href} class="fr-text--sm mb-0! font-medium bg-none! hover:underline">
          {step.label}
          <span class="sr-only">
            : {numberFormatter.format(step.count)}
            {#if previous}
              ({m['admin.activity.overview.funnel.continue']({
                share: percentFormatter.format(previous.count ? step.count / previous.count : 0)
              })})
            {/if}
          </span>
        </a>
        <div class="h-6 flex justify-center" aria-hidden="true">
          <div
            class="rounded h-full bg-[--blue-france-main-525]"
            style:width="{width(step.count)}%"
          ></div>
        </div>
        <p class="text-base mb-0! font-bold tabular-nums" aria-hidden="true">
          {numberFormatter.format(step.count)}
        </p>
      </li>
    {/each}
  </ol>
</section>

<style>
  /* DSFR numbers ordered lists; the order here is in the shape itself. */
  .funnel {
    margin: 0;
    padding: 0;
    list-style: none;
  }
  .funnel > li {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.25rem 1rem;
    align-items: center;
    padding: 0;
  }
  .funnel > li::before {
    content: none;
  }
  .funnel-gap > span:first-child {
    display: none;
  }
  @media (min-width: 48em) {
    .funnel > li {
      grid-template-columns: 13rem 1fr 7.5rem;
    }
    .funnel-gap > span:first-child {
      display: block;
    }
  }
</style>
