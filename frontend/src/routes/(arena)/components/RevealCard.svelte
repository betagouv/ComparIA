<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import Dropdown from '$components/Dropdown.svelte'
  import { Badge, Button, Icon } from '$components/dsfr'
  import InfoCard from '$components/InfoCard.svelte'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import MiniCard from './MiniCard.svelte'
  import type { RevealModelData } from '$lib/chatService.svelte'
  import { buildConsumptionSummary, formatLocalizedNumber } from '$lib/consumptionSummary'
  import { buildCostComparison } from '$lib/costComparison'
  import { formatUsageCostFromEuro } from '$lib/currency'
  import { buildEnergyEquivalences } from '$lib/energyEquivalences'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { ENERGY_CLASS_COLORS, getModelCards, getModelsContext } from '$lib/models'
  import { propsToAttrs, sanitize } from '$lib/utils/commons'
  import { buildUsageConsumption, USAGE_PROFILES, type UsageProfileId } from '$lib/usageProfiles'

  let {
    data,
    otherData,
    selected,
    usageProfile,
    onUsageProfileChange,
    impactTab,
    onImpactTabChange,
    modelTitleHeight,
    onModelTitleHeightChange
  }: {
    data: RevealModelData
    otherData: RevealModelData
    selected: boolean
    usageProfile: UsageProfileId
    onUsageProfileChange: (profile: UsageProfileId) => void
    impactTab: 'explanation' | 'equivalences'
    onImpactTabChange: (tab: 'explanation' | 'equivalences') => void
    modelTitleHeight: number
    onModelTitleHeightChange: (height: number) => void
  } = $props()
  let modelTitle = $state<HTMLDivElement>()

  $effect(() => {
    if (!modelTitle) return

    const updateHeight = () => onModelTitleHeightChange(modelTitle!.getBoundingClientRect().height)
    const observer = new ResizeObserver(updateHeight)
    observer.observe(modelTitle)
    updateHeight()

    return () => observer.disconnect()
  })
  const { models, commons } = getModelsContext()
  const model = $derived(models.find((llm) => llm.id === data.id)!)
  const otherModel = $derived(models.find((llm) => llm.id === otherData.id)!)
  const usage = $derived(USAGE_PROFILES[usageProfile])
  const usageData = $derived(
    buildUsageConsumption(
      usage,
      {
        inputTokens: data.input_tokens,
        outputTokens: data.tokens,
        totalTokens: data.total_tokens,
        energyMwh: data.energy_mwh
      },
      model.wh_per_million_token
    )
  )
  const otherUsageData = $derived(
    buildUsageConsumption(
      usage,
      {
        inputTokens: otherData.input_tokens,
        outputTokens: otherData.tokens,
        totalTokens: otherData.total_tokens,
        energyMwh: otherData.energy_mwh
      },
      otherModel.wh_per_million_token
    )
  )
  const usageLabel = $derived(m[`reveal.impacts.usage.${usageProfile}`]())
  const usageOptions = $derived([
    {
      value: 'discussion' as const,
      heading: m['reveal.impacts.usage.headingDiscussion'](),
      label: m['reveal.impacts.usage.menuDiscussion'](),
      description: m['reveal.impacts.usage.descriptionDiscussion']()
    },
    {
      value: 'research' as const,
      heading: m['reveal.impacts.usage.headingResearch'](),
      label: m['reveal.impacts.usage.menuResearch'](),
      description: m['reveal.impacts.usage.descriptionResearch']()
    },
    {
      value: 'coding' as const,
      heading: m['reveal.impacts.usage.headingCoding'](),
      label: m['reveal.impacts.usage.menuCoding'](),
      description: m['reveal.impacts.usage.descriptionCoding']()
    }
  ])
  const selectedUsageOption = $derived(
    usageOptions.find((option) => option.value === usageProfile)!
  )
  const consumptionSummary = $derived(
    buildConsumptionSummary(
      model,
      otherModel,
      { tokens: usageData.outputTokens, energy_mwh: usageData.energyMwh, usage: usageLabel },
      { tokens: otherUsageData.outputTokens, energy_mwh: otherUsageData.energyMwh }
    )
  )
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
    (model.price_in / 1_000_000) * usageData.inputTokens +
      (model.price_out / 1_000_000) * usageData.outputTokens
  )
  const otherCost = $derived(
    (otherModel.price_in / 1_000_000) * otherUsageData.inputTokens +
      (otherModel.price_out / 1_000_000) * otherUsageData.outputTokens
  )
  const formattedCost = $derived(formatUsageCostFromEuro(cost, commons.currency, getLocale()))
  const costComparison = $derived(buildCostComparison(cost, otherCost))
  const energyComparison = $derived(
    buildCostComparison(usageData.energyMwh, otherUsageData.energyMwh)
  )
  const costComparisonText = $derived.by(() => {
    switch (costComparison.kind) {
      case 'more':
        return m['reveal.impacts.cost.comparison.more']({
          factor: formatLocalizedNumber(costComparison.factor, 1)
        })
      case 'less':
        return m['reveal.impacts.cost.comparison.less']({
          factor: formatLocalizedNumber(costComparison.factor, 1)
        })
      case 'similar':
        return m['reveal.impacts.cost.comparison.similar']()
      case 'unavailable':
        return m['reveal.impacts.cost.comparison.unavailable']()
    }
  })
  const energyComparisonText = $derived.by(() => {
    switch (energyComparison.kind) {
      case 'more':
        return m['reveal.impacts.energy.comparison.more']({
          factor: formatLocalizedNumber(energyComparison.factor, 1)
        })
      case 'less':
        return m['reveal.impacts.energy.comparison.less']({
          factor: formatLocalizedNumber(energyComparison.factor, 1)
        })
      case 'similar':
        return m['reveal.impacts.energy.comparison.similar']()
      case 'unavailable':
        return m['reveal.impacts.energy.comparison.unavailable']()
    }
  })
  const energyEquivalences = $derived(buildEnergyEquivalences(usageData.energyMwh, getLocale()))

  const impactTabs = $derived([
    { id: 'explanation' as const, label: m['reveal.impacts.how.tabs.explanation']() },
    { id: 'equivalences' as const, label: m['reveal.impacts.how.tabs.equivalences']() }
  ])
  const equivalenceCards = $derived([
    {
      id: 'video' as const,
      icon: 'i-ri-youtube-fill',
      iconClass: 'text-[--red-marianne-main-472]',
      title: m['reveal.impacts.energy.equivalences.video.title'](),
      tooltip: m['reveal.impacts.energy.equivalences.video.tooltip'](),
      value: energyEquivalences?.videoDuration
    },
    {
      id: 'led' as const,
      icon: 'i-ri-lightbulb-fill',
      iconClass: 'text-[--yellow-tournesol-main-731]',
      title: m['reveal.impacts.energy.equivalences.led.title'](),
      tooltip: m['reveal.impacts.energy.equivalences.led.tooltip'](),
      value: energyEquivalences?.ledDuration
    },
    {
      id: 'phone' as const,
      icon: 'i-ri-battery-charge-fill',
      iconClass: 'text-info',
      title: m['reveal.impacts.energy.equivalences.phone.title'](),
      tooltip: m['reveal.impacts.energy.equivalences.phone.tooltip'](),
      value: energyEquivalences?.phoneBatteryPercentage
    }
  ])

  function selectTab<T extends string>(
    event: KeyboardEvent,
    tabIds: readonly T[],
    currentTab: T,
    setTab: (tab: T) => void
  ) {
    const currentIndex = tabIds.indexOf(currentTab)
    let nextIndex: number | undefined

    if (event.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + tabIds.length) % tabIds.length
    if (event.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabIds.length
    if (event.key === 'Home') nextIndex = 0
    if (event.key === 'End') nextIndex = tabIds.length - 1
    if (nextIndex === undefined) return

    event.preventDefault()
    const nextTab = tabIds[nextIndex]
    setTab(nextTab)
    document.getElementById(`${data.id}-${nextTab}-tab`)?.focus()
  }
  const consoCards = $derived([
    {
      id: 'conso-tokens' as const,
      icon: 'i-ri-ai-generate-text',
      title: m['reveal.impacts.tokens.title'](),
      tooltip: m['reveal.impacts.tokens.tooltip'](),
      content: m['reveal.impacts.tokens.used']({
        count: usageData.totalTokens,
        midProps,
        smallProps
      }),
      subContent: model.context_tokens
        ? m['reveal.impacts.tokens.max']({ count: Math.floor(model.context_tokens / 1000) })
        : m['words.NA']()
    }
  ])
</script>

<div class="cg-border bg-white p-5 md:p-7 md:pb-10 flex h-full flex-col">
  <div>
    <h2
      class="fr-h6 mb-4! text-dark-grey! gap-2 flex items-start"
      style="min-height: {Math.max(40, modelTitleHeight)}px"
    >
      <AILogo logo={model.lab.logo} size="lg" alt={model.lab.name} />
      <div bind:this={modelTitle} class="min-w-0 flex-1">
        <span class="font-normal">{model.lab.name}/</span>{model.name}
      </div>
      {#if selected}
        <div
          class="border-primary px-3 font-bold ms-auto shrink-0 rounded-[3.75rem] border bg-[--blue-france-975-75] text-[14px] text-nowrap text-[--text-title-blue-france]"
        >
          {m['vote.yours']()}
        </div>
      {/if}
    </h2>
    <ul class="fr-badges-group mb-4!">
      {#each modelBadges as badge, i (i)}
        <!-- id after the spread: the badge carries its own id, shared with the
             model modal, and two elements can't answer to the same one. -->
        <li><Badge {...badge} id="{model.id}-card-badge-{i}" size="sm" noTooltip /></li>
      {/each}
    </ul>
  </div>

  <!-- The floor is what "Niveau d'ouverture" and the size badge need to fit.
       Any narrower and DSFR's break-word splits them mid-word. -->
  <div class="gap-4 grid grid-cols-[repeat(auto-fit,minmax(9.75rem,1fr))]">
    {#each cards as card, i (i)}
      <InfoCard
        {...card}
        id="{model.id}-{card.id}"
        titleTag="h3"
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
    <h3 class="text-sm! mb-1! gap-1 mt-auto! flex flex-wrap items-center text-left!">
      <!-- Wraps: this label is 5 characters in French and 32 in Swedish. -->
      <span class="text-dark-grey! font-bold">{m['reveal.impacts.title']()}</span>
      <Dropdown
        id="usage-profile-{data.pos}"
        label={m['reveal.impacts.usage.changeLabel']()}
        closeOnSelect
        role="menu"
        buttonClass="border-primary text-primary py-1! px-2! rounded-full! border bg-white text-sm! text-left! font-bold inline-flex w-fit! max-w-full! items-center justify-start! gap-1 shadow-sm hover:bg-[--blue-france-975-75] focus:bg-[--blue-france-975-75]"
        class="p-1 w-fit! max-w-full"
      >
        {#snippet buttonLabel()}
          <span class="text-left!">{selectedUsageOption.heading}</span>
          <Icon icon="i-ri-arrow-down-s-line shrink-0" size="sm" aria-hidden="true" />
        {/snippet}
        <ul class="m-0! p-0! list-none">
          {#each usageOptions as option (option.value)}
            <li>
              <button
                type="button"
                role="menuitemradio"
                aria-checked={usageProfile === option.value}
                class="py-2! px-3! flex w-full items-center justify-between border-0 bg-transparent text-left hover:bg-[--blue-france-975-75] focus:bg-[--blue-france-975-75]"
                onclick={() => onUsageProfileChange(option.value)}
              >
                <span>{option.label}</span>
                {#if usageProfile === option.value}
                  <Icon icon="i-ri-check-line" size="sm" aria-hidden="true" />
                {/if}
              </button>
            </li>
          {/each}
        </ul>
      </Dropdown>
    </h3>
    <p class="text-xxs! text-grey mb-3!">{selectedUsageOption.description}</p>
    {#if usageProfile !== 'discussion'}
      <p class="text-xxs! text-grey mb-3! -mt-2!">{m['reveal.impacts.usage.assumption']()}</p>
    {/if}
    <div class="gap-4 flex flex-col">
      <div class="gap-2 2xl:grid-cols-3 xl:grid-cols-2 md:grid-cols-1 sm:grid-cols-2 grid">
        {#each consoCards as card (card.id)}
          <InfoCard
            {...card}
            id="{model.id}-{card.id}"
            titleTag="h4"
            iconClass="text-info"
            size="sm"
          />
        {/each}
        <InfoCard
          id="{model.id}-conso-cost"
          icon="i-ri-coins-line"
          titleTag="h4"
          title={m['reveal.impacts.cost.title']()}
          tooltip={m['reveal.impacts.cost.tooltip']()}
          iconClass="text-info"
          size="sm"
        >
          <p class="text-base! mb-1! font-bold leading-[1.1]!">{formattedCost}</p>
          <p class="text-xxs! text-grey mb-1!">{m['reveal.impacts.cost.sub']()}</p>
          <div
            class={[
              'gap-1 text-xxs! flex items-center',
              {
                'text-error': costComparison.kind === 'more',
                'text-success': costComparison.kind === 'less',
                'text-grey':
                  costComparison.kind === 'similar' || costComparison.kind === 'unavailable'
              }
            ]}
          >
            {#if costComparison.kind === 'more' || costComparison.kind === 'less'}
              <Icon
                icon="i-ri-triangle-fill"
                size="xs"
                class={costComparison.kind === 'less' ? 'rotate-180' : undefined}
                aria-hidden="true"
              />
            {/if}
            <span>{costComparisonText}</span>
          </div>
        </InfoCard>
        <InfoCard
          id="{model.id}-conso-energy"
          icon="i-ri-flashlight-fill"
          titleTag="h4"
          title={m['reveal.impacts.energy.title']()}
          tooltip={`${m['reveal.impacts.energy.tooltip']()} ${m['reveal.impacts.energy.estimate']()}`}
          iconClass="text-info"
          size="sm"
        >
          <p class="text-base! mb-1! font-bold leading-[1.1]!">
            {@html sanitize(
              m['reveal.impacts.energy.conso']({
                count: usageData.energyMwh.toFixed(usageData.energyMwh < 2 ? 2 : 0),
                midProps
              })
            )}
          </p>
          <div
            class={[
              'gap-1 text-xxs! flex items-center',
              {
                'text-error': energyComparison.kind === 'more',
                'text-success': energyComparison.kind === 'less',
                'text-grey':
                  energyComparison.kind === 'similar' || energyComparison.kind === 'unavailable'
              }
            ]}
          >
            {#if energyComparison.kind === 'more' || energyComparison.kind === 'less'}
              <Icon
                icon="i-ri-triangle-fill"
                size="xs"
                class={energyComparison.kind === 'less' ? 'rotate-180' : undefined}
                aria-hidden="true"
              />
            {/if}
            <span>{energyComparisonText}</span>
          </div>
        </InfoCard>
      </div>

      <article class="cg-border bg-white">
        <div class="px-3 pt-3">
          <div
            class="rounded-md p-1 gap-1 inline-flex items-center bg-[--blue-france-975-75]"
            role="tablist"
            aria-label={m['reveal.impacts.how.tabs.label']()}
          >
            {#each impactTabs as tab (tab.id)}
              <button
                id="{data.id}-{tab.id}-tab"
                type="button"
                role="tab"
                aria-selected={impactTab === tab.id}
                aria-controls="{data.id}-{tab.id}-panel"
                tabindex={impactTab === tab.id ? 0 : -1}
                class="rounded-sm px-3 py-1.5 text-xs font-bold border-0 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[--blue-france-sun-113]"
                class:bg-white={impactTab === tab.id}
                class:text-primary={impactTab === tab.id}
                class:shadow-sm={impactTab === tab.id}
                class:text-grey={impactTab !== tab.id}
                class:hover:bg-white={impactTab !== tab.id}
                class:hover:text-primary={impactTab !== tab.id}
                onclick={() => onImpactTabChange(tab.id)}
                onkeydown={(event) =>
                  selectTab(event, ['explanation', 'equivalences'], impactTab, onImpactTabChange)}
                >{tab.label}</button
              >
            {/each}
          </div>
        </div>

        <div
          id="{data.id}-explanation-panel"
          role="tabpanel"
          aria-labelledby="{data.id}-explanation-tab"
          hidden={impactTab !== 'explanation'}
          class="p-3"
        >
          <p class="text-xs! mb-0!">
            {@html sanitize(consumptionSummary.classification)}
            <br />
            {@html sanitize(consumptionSummary.consumption)}
          </p>
        </div>

        <div
          id="{data.id}-equivalences-panel"
          role="tabpanel"
          aria-labelledby="{data.id}-equivalences-tab"
          hidden={impactTab !== 'equivalences'}
          class="p-3"
        >
          {#if energyEquivalences}
            <div class="mb-2">
              <p class="text-xs! text-grey mb-0!">
                {m['reveal.impacts.energy.equivalences.intro']()}
              </p>
            </div>
            <div class="gap-1.5 sm:grid-cols-3 min-w-0 grid grid-cols-1">
              {#each equivalenceCards as card (card.id)}
                <MiniCard
                  id="equivalence-{card.id}-{data.pos}"
                  value={card.value ?? ''}
                  desc={card.title}
                  tooltip={card.tooltip}
                  icon={card.icon}
                  iconClass={card.iconClass}
                  compact
                  class="min-w-0 bg-white p-1.5!"
                />
              {/each}
            </div>
          {:else}
            <p class="text-xs! text-grey mb-0!">
              {m['reveal.impacts.energy.equivalences.unavailable']()}
            </p>
          {/if}
        </div>
      </article>
    </div>
  </div>

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
