<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Button, Tooltip } from '$components/dsfr'
  import InfoCard from '$components/InfoCard.svelte'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import type { RevealModelData } from '$lib/chatService.svelte'
  import { buildConsumptionSummary } from '$lib/consumptionSummary'
  import { formatUsageCostFromEuro } from '$lib/currency'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { ENERGY_CLASS_COLORS, getModelCards, getModelsContext } from '$lib/models'
  import { propsToAttrs, sanitize } from '$lib/utils/commons'

  let {
    data,
    otherData,
    selected
  }: { data: RevealModelData; otherData: RevealModelData; selected: boolean } = $props()
  const { models, commons } = getModelsContext()
  const model = $derived(models.find((llm) => llm.id === data.id)!)
  const otherModel = $derived(models.find((llm) => llm.id === otherData.id)!)
  const consumptionSummary = $derived(buildConsumptionSummary(model, otherModel, data, otherData))
  const modelBadges = $derived(
    (['license', 'size', 'release'] as const).map((k) => model.badges[k]).filter((b) => !!b)
  )
  const baseCards = $derived(getModelCards(model, 'sm', commons))
  const cards = $derived([
    baseCards.size,
    baseCards.arch,
    baseCards.sovereignty,
    baseCards.rank,
    baseCards.energy
  ])

  const midProps = propsToAttrs({ class: 'text-xs!' })
  const smallProps = propsToAttrs({ class: 'text-xxs!' })
  const cost = $derived(
    (model.price_in / 1_000_000) * data.input_tokens + (model.price_out / 1_000_000) * data.tokens
  )
  const formattedCost = $derived(formatUsageCostFromEuro(cost, commons.currency, getLocale()))
  const consoCards = $derived([
    {
      id: 'conso-tokens' as const,
      icon: 'i-ri-ai-generate-text',
      title: m['reveal.impacts.tokens.title'](),
      tooltip: m['reveal.impacts.tokens.tooltip'](),
      content: m['reveal.impacts.tokens.used']({
        count: data.total_tokens,
        midProps,
        smallProps
      }),
      subContent: model.context_tokens
        ? m['reveal.impacts.tokens.max']({ count: Math.floor(model.context_tokens / 1000) })
        : m['words.NA']()
    },
    {
      id: 'conso-cost' as const,
      icon: 'i-ri-coins-line',
      title: m['reveal.impacts.cost.title'](),
      tooltip: m['reveal.impacts.cost.tooltip'](),
      content: formattedCost,
      subContent: m['reveal.impacts.cost.sub']()
    },
    {
      id: 'conso-energy' as const,
      icon: 'i-ri-flashlight-fill',
      title: m['reveal.impacts.energy.title'](),
      tooltip: m['reveal.impacts.energy.tooltip'](),
      content:
        model.license.kind !== 'proprietary'
          ? m['reveal.impacts.energy.conso']({
              count: data.energy_mwh.toFixed(data.energy_mwh < 2 ? 2 : 0),
              midProps
            })
          : m['reveal.impacts.energy.conso_estimated']({
              count: data.energy_mwh.toFixed(data.energy_mwh < 2 ? 2 : 0),
              midProps,
              smallProps
            })
    }
  ])

  // FIXME equivalences legacy?
  // const conso = $derived.by(() => {
  //   const co2 = data.scaled_co2_t
  //   return {
  //     energy: data.energy_mwh.toFixed(data.energy_mwh < 2 ? 2 : 0)
  //     co2: co2 < 1 ? co2.toFixed(3) : co2 < 10 ? co2.toFixed(1) : co2.toFixed(0)
  //   }
  // })
  // const i18nData = getI18nContext()
  // const equivalencesData: Record<
  //   EquivalenceType,
  //   { emoji: string; source: string; unit?: string; decimals?: number }
  // > = {
  //   paris_nyc_flights: {
  //     emoji: '✈️',
  //     decimals: 1,
  //     source: 'https://impactco2.fr/outils/transport/avion-longcourrier'
  //   },
  //   baguette_production: {
  //     emoji: '🥖',
  //     unit: 'kg',
  //     source: 'https://impactco2.fr/outils/alimentation/baguette'
  //   },
  //   one_year_tree_absortion: {
  //     emoji: '🌳',
  //     source: 'https://www.usda.gov/about-usda/news/blog/power-one-tree-very-air-we-breathe'
  //   },
  //   package_delivery: {
  //     emoji: '📦',
  //     source: 'https://impactco2.fr/outils/livraison/livraisondomicile'
  //   },
  //   mango_import: {
  //     emoji: '🥭',
  //     unit: 'kg',
  //     source: 'https://impactco2.fr/outils/fruitsetlegumes/mangue'
  //   },
  //   pool_filing: { emoji: '💦', source: 'https://impactco2.fr/outils/caspratiques/piscine' }
  // }

  // let containerElem = $state<HTMLDivElement>()
  // let scrollable = $state({ left: false, right: false })

  // function checkIfScollable() {
  //   scrollable.left = containerElem!.scrollLeft !== 0
  //   scrollable.right =
  //     Math.round(containerElem!.offsetWidth + containerElem!.scrollLeft) <
  //     containerElem!.scrollWidth
  // }

  // function scrollEquivalence(direction: -1 | 1) {
  //   const { offsetWidth, scrollLeft } = containerElem!
  //   const cols = Array.from(containerElem!.querySelectorAll<HTMLHtmlElement>('.eq-card')).reverse()
  //   const col = cols.find((col) => {
  //     const offsetLeft = col.offsetLeft - direction
  //     return direction === 1 ? offsetLeft <= offsetWidth + scrollLeft : offsetLeft <= scrollLeft
  //   })

  //   if (!col) return
  //   containerElem!.scrollTo({
  //     left: direction === 1 ? col.offsetLeft + col.offsetWidth - offsetWidth : col.offsetLeft
  //   })
  // }

  // onMount(() => {
  //   checkIfScollable()
  // })
</script>

<!-- FIXME equivalences legacy? -->
<!-- <svelte:window onresize={() => checkIfScollable()} {onscroll} /> -->

<div class="cg-border bg-white p-5 md:p-7 md:pb-10 flex h-full flex-col">
  <div>
    <h5 class="fr-h6 mb-4! text-dark-grey! gap-2 flex items-center">
      <AILogo logo={model.lab.logo} size="lg" alt={model.lab.name} />
      <div><span class="font-normal">{model.lab.name}/</span>{model.name}</div>
      {#if selected}
        <div
          class="border-primary text-primary px-3 font-bold ms-auto rounded-[3.75rem] border bg-[--blue-france-975-75] text-[14px] text-nowrap"
        >
          {m['vote.yours']()}
        </div>
      {/if}
    </h5>
    <ul class="fr-badges-group mb-4!">
      {#each modelBadges as badge, i (i)}
        <li><Badge id="card-badge-{i}" {...badge} size="sm" noTooltip /></li>
      {/each}
    </ul>
  </div>

  <div class="gap-4 sm:grid-cols-3 md:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-5 grid grid-cols-2">
    {#each cards as card, i (i)}
      <InfoCard
        {...card}
        id="{model.id}-{card.id}"
        iconClass={'iconClass' in card ? card.iconClass : 'text-info'}
        titleClass="3xl:flex-row lg:flex-col"
        size="xs"
      >
        {#if card.id === 'energy'}
          <div class="gap-1 mt-1 flex flex-col">
            <div
              class="ps-2 w-80% text-sm text-white font-bold h-5 flex items-center justify-start"
              style="background-color: var({ENERGY_CLASS_COLORS[
                model.energy_class
              ]}); clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 50%, calc(100% - 10px) 100%, 0 100%);"
            >
              {model.energy_class}
            </div>
          </div>
        {/if}
      </InfoCard>
    {/each}
  </div>

  <div class="mt-8 cg-border rounded-sm! bg-light-grey p-3 pb-5">
    <h6 class="mb-3! text-base! mt-auto!">
      {m['reveal.impacts.title']()}
      <Tooltip id="impact-{data.pos}" text={m['reveal.impacts.tooltip']()} />
    </h6>
    <div class="gap-4 flex flex-col">
      <div class="gap-2 2xl:grid-cols-3 xl:grid-cols-2 md:grid-cols-1 sm:grid-cols-2 grid">
        {#each consoCards as card (card.id)}
          <InfoCard {...card} id="{model.id}-{card.id}" iconClass="text-info" size="sm" />
        {/each}
      </div>

      <article class="cg-border bg-white p-3 flex flex-col">
        <p class="text-xs! text-info mb-1!">{m['reveal.impacts.how.title']()}</p>
        <p class="text-xs! mb-0!">
          {@html sanitize(consumptionSummary.classification)}
          <br />
          {@html sanitize(consumptionSummary.consumption)}
        </p>
      </article>
    </div>
  </div>

  <!-- FIXME equivalences legacy? -->
  <!-- <div class="mt-6! md:mt-9! cg-border rounded-sm! bg-very-light-grey">
    <div class="p-3 bg-light-grey">
      <h6 class="text-base! mb-2!">
        {m['reveal.equivalent.title']()}
        <Tooltip id="equivalent-{data.pos}">
          {@html sanitize(
            m['reveal.equivalent.title_tooltip']({
              linkProps: externalLinkProps({
                href: i18nData.peopleUsingAIDataLink
              })
            })
          )}
        </Tooltip>
      </h6>
      <div class="gap-6 sm:flex-row flex flex-col items-start">
        <p class="text-grey! md:text-[13px]! mb-0! lh-normal! text-[12px]!">
          {m['reveal.equivalent.desc']()}
        </p>

        <MiniCard
          id="co2-{data.pos}"
          value={conso.co2}
          units={m['reveal.equivalent.co2.unit']()}
          icon="i-ri-cloudy-2-fill"
          iconClass="text-[--grey-975-75-active]"
          desc={m['reveal.equivalent.co2.label']()}
          tooltip={m['reveal.equivalent.co2.tooltip']()}
          class="bg-white xl:-mt-6 min-w-[180px]"
        />
      </div>
    </div>

    <div class="py-3 flex max-w-full items-center">
      <Button
        text={m['actions.scrollLeft']()}
        icon="arrow-left-line"
        iconOnly
        variant="tertiary"
        disabled={!scrollable.left}
        onclick={() => scrollEquivalence(-1)}
        class="mx-5"
      />
      <div
        bind:this={containerElem}
        onscroll={() => checkIfScollable()}
        class="pb-3 relative flex w-full overflow-auto"
      >
        {#each data.equivalences as eq, i (i)}
          <div
            class="eq-card sm:min-w-1/2 md:min-w-1/3 lg:min-w-1/2 xl:min-w-1/3 px-2 flex min-w-full flex-col items-center"
          >
            <div class="mb-1 text-[20px]">
              {equivalencesData[eq.type].emoji}
            </div>

            <strong class="text-[18px]">
              {eq.value.toFixed(equivalencesData[eq.type].decimals ?? 0)}
              {@html sanitize(equivalencesData[eq.type].unit ?? '')}
            </strong>
            <p class="mb-0! text-grey! lh-tight text-center text-[11px]!">
              {m[`reveal.equivalent.scales.${eq.type}.unit`]()}
              <Tooltip id="equivalent-{eq.type}-{data.pos}">
                {@html sanitize(
                  m[`reveal.equivalent.scales.${eq.type}.tooltip`]({
                    linkProps: externalLinkProps({
                      href: equivalencesData[eq.type].source
                    })
                  })
                )}
              </Tooltip>
            </p>
          </div>
        {/each}
      </div>
      <Button
        text={m['actions.scrollRight']()}
        icon="arrow-right-line"
        iconOnly
        variant="tertiary"
        disabled={!scrollable.right}
        class="mx-5"
        onclick={() => scrollEquivalence(1)}
      />
    </div>
  </div> -->

  <div class="mt-9 text-center">
    <Button
      text={m['actions.seeMore']()}
      data-fr-opened="false"
      aria-controls="modal-model-reveal-{model.id}"
      size="sm"
    />
  </div>
</div>

<ModelInfoModal {commons} {model} modalId="modal-model-reveal-{model.id}" />
