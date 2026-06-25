<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Button, Icon, Tooltip } from '$components/dsfr'
  import InfoCard from '$components/InfoCard.svelte'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import type { RevealModelData } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { ENERGY_CLASS_COLORS, getModelCards, getModelsContext, MODALITIES } from '$lib/models'
  import { sanitize } from '$lib/utils/commons'
  import { MiniCard } from '.'

  let { data, selected }: { data: RevealModelData; selected: boolean } = $props()
  const { models, commons } = getModelsContext()
  const model = $derived(models.find((llm) => llm.id === data.id)!)
  const modelBadges = $derived(
    (['license', 'size', 'release'] as const).map((k) => model.badges[k]).filter((b) => !!b)
  )
  const cards = $derived.by(() => {
    const cards = getModelCards(model, 'sm', commons)
    return [
      cards.size,
      cards.arch,
      cards.context,
      cards.modalities,
      cards.price,
      cards.sovereignty,
      cards.rank,
      cards.energy
    ]
  })
  const conso = $derived.by(() => {
    const co2 = data.scaled_co2_t
    return {
      energy: data.energy_mwh.toFixed(data.energy_mwh < 2 ? 2 : 0),
      co2: co2 < 1 ? co2.toFixed(3) : co2 < 10 ? co2.toFixed(1) : co2.toFixed(0)
    }
  })

  // FIXME equivalences legacy?
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

  <div class="gap-4 sm:grid-cols-2 md:grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 grid">
    {#each cards as card, i (i)}
      <InfoCard {...card} id="{model.id}-{card.id}" iconClass="text-info" size="sm">
        {#if card.id === 'price'}
          <div class="gap-2 flex w-full flex-wrap justify-between">
            {#each card.contents as c, i (i)}
              <div class="">
                <p class="mb-0! font-bold text-lg! leading-[1.1]!">
                  ${@html sanitize(c.content)}
                </p>
                <p class="text-xxs! text-grey mb-0!">
                  {c.subContent}
                </p>
              </div>
            {/each}
          </div>
        {:else if card.id === 'modalities'}
          <div class="gap-2 flex flex-wrap justify-between">
            {#each MODALITIES as mod (mod.id)}
              {@const active = model.inputs.includes(mod.id)}
              <div
                class="text-xxs gap-1 flex flex-col items-center"
                aria-hidden={active ? 'false' : 'true'}
              >
                <Icon
                  icon={mod.icon}
                  size="xs"
                  block
                  class={active ? 'text-primary' : 'text-[#B3B3B3]'}
                />
                <span class={{ 'text-[#B3B3B3]': !active }}>{mod.title}</span>
              </div>
            {/each}
          </div>
        {:else if card.id === 'energy'}
          <div
            class="ps-2 w-80% text-white font-bold flex h-full items-center justify-start"
            style="background-color: {ENERGY_CLASS_COLORS[
              model.energy_class
            ]}; clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 50%, calc(100% - 10px) 100%, 0 100%);"
          >
            {model.energy_class}
          </div>
        {/if}
      </InfoCard>
    {/each}
  </div>

  <div class="mt-8 cg-border rounded-sm! bg-light-grey p-3 pb-11">
    <h6 class="mb-5! text-base! mt-auto!">
      {m['reveal.impacts.title']()}
      <Tooltip id="impact-{data.pos}" text={m['reveal.impacts.tooltip']()} />
    </h6>
    <div class="flex">
      <div class="md:basis-2/3 md:flex-row flex basis-1/2 flex-col">
        <div class="md:w-full relative">
          <MiniCard
            id="params-{data.pos}"
            value={model.params}
            desc={m['reveal.impacts.size.label']()}
            tooltip={m['models.openWeight.tooltips.params']()}
            class="-mb-2 bg-white z-1 h-full "
          >
            {m['reveal.impacts.size.count']()}
            {#if model.license.kind === 'proprietary'}
              {m['reveal.impacts.size.estimated']()}
            {/if}
            {#if model.quantization === 'q8'}
              {m['reveal.impacts.size.quantized']()}
            {/if}
          </MiniCard>
          <div
            class="cg-border rounded-sm! p-1 ps-3 pt-2 leading-normal absolute z-0 flex w-full bg-[--beige-gris-galet-950-100] text-[11px]"
          >
            <span class="text-[--beige-gris-galet-sun-407-moon-821]">
              {model.badges.arch.text}
            </span>
            <Tooltip
              id="{model.id}-arch-tooltip"
              size="xs"
              text={model.badges.arch.tooltip}
              class="ms-auto"
            />
          </div>
        </div>

        <strong class="mb-1 md:mx-1 md:my-auto m-auto text-[20px]">×</strong>

        <MiniCard
          id="tokens-{data.pos}"
          value={data.tokens}
          units={m['reveal.impacts.tokens.tokens']()}
          desc={m['reveal.impacts.tokens.label']()}
          tooltip={m['reveal.impacts.tokens.tooltip']()}
          class="md:w-full bg-white"
        />
      </div>

      <div class="md:basis-1/3 flex basis-1/2 items-center">
        <strong class="m-auto">≈</strong>

        <MiniCard
          id="energy-{data.pos}"
          value={conso.energy}
          units="mWh"
          desc={m['reveal.impacts.energy.label']()}
          icon="i-ri-flashlight-fill"
          iconClass="text-info"
          tooltip={m['reveal.impacts.energy.tooltip']()}
          class="bg-white h-fit"
        />
      </div>
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
