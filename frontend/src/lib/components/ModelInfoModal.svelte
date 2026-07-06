<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Button, Icon, Link, Tooltip } from '$components/dsfr'
  import { ENERGY_CLASSES } from '$lib/generated/constants'
  import { m } from '$lib/i18n/messages'
  import type { BotModel, Commons } from '$lib/models'
  import { ENERGY_CLASS_COLORS, getModelCards, MODALITIES } from '$lib/models'
  import { sanitize } from '$lib/utils/commons'
  import type { ClassValue } from 'svelte/elements'
  import InfoCard from './InfoCard.svelte'

  let {
    model,
    modalId,
    commons,
    onClose
  }: { model?: BotModel; modalId: string; commons: Commons; onClose?: () => void } = $props()

  const badges = $derived.by(() => {
    if (!model) return []
    const { release, knowledge } = model.badges
    return [release, knowledge].filter((b) => !!b)
  })

  const dsfrEvents = {
    'ondsfr.conceal': () => onClose?.()
  }
  const cards = $derived.by(() => {
    if (!model) return {}
    const cards = getModelCards(model, 'md', commons)

    return {
      technical: [cards.size, cards.arch, cards.context, cards.price, cards.modalities],
      energy: cards.energy,
      rank: cards.rank
    } as const
  })

  const sovFields = $derived.by(() => {
    if (!model) return []
    const fields = [
      { id: 'license_type', value: model.badges.license },
      { id: 'license_name', value: model.license.name },
      { id: 'reuse', value: model.license.reuse },
      { id: 'commercial_use', value: model.license.commercial_use },
      { id: 'public_weights', value: model.public_weights },
      { id: 'public_training_data', value: model.public_training_data },
      { id: 'public_training_code', value: model.public_training_code },
      { id: 'origin_country', value: model.lab.origin_country },
      { id: 'eu_hostable', value: model.eu_hostable }
    ] as const

    return model.license.kind === 'proprietary'
      ? fields.filter((field) => field.id !== 'license_name')
      : fields
  })

  const hardwares = [
    { tier: 'smartphone' as const, icon: 'i-ri-smartphone-line' },
    { tier: 'laptop' as const, icon: 'i-ri-computer-line' },
    { tier: 'workstation' as const, icon: 'i-ri-hard-drive-3-line' },
    { tier: 'server' as const, icon: 'i-ri-server-line' }
  ]
  type HardwareTier = (typeof hardwares)[number]['tier']
  const hardware = $derived.by(() => {
    if (!model) return

    function ramToHardwareTier(ramGb: number): {
      tier: HardwareTier
      icon: string
      gpuCount: number
    } {
      const gpuCount = Math.max(1, Math.ceil(ramGb / 80)) // ~80 GB / GPU
      if (ramGb <= 3) return { ...hardwares[0], gpuCount }
      if (ramGb <= 16) return { ...hardwares[1], gpuCount }
      if (gpuCount <= 1) return { ...hardwares[2], gpuCount }
      return { ...hardwares[3], gpuCount }
    }

    return ramToHardwareTier(model.required_ram)
  })

  const energyRows = ENERGY_CLASSES.map((letter, i) => ({
    letter,
    color: ENERGY_CLASS_COLORS[letter],
    width: 50 + (50 / ENERGY_CLASSES.length) * (i + 1)
  }))

  const rankingRows = [
    { c: '1', emoji: '🥇' },
    { c: '2', emoji: '🥈' },
    { c: '3', emoji: '🥉' },
    { c: '4', emoji: '4️⃣' },
    { c: '5', emoji: '5️⃣' }
  ] as const
</script>

{#snippet iconHeading({
  icon,
  title,
  tag = 'h2',
  iconClass = 'text-info',
  classes = 'mb-0!'
}: {
  icon: string
  title: string
  tag?: string
  iconClass?: ClassValue
  classes?: ClassValue
})}
  <svelte:element this={tag} class={['text-sm gap-1 font-normal flex items-center', classes]}>
    <Icon {icon} size="xs" block class={iconClass} />
    {title}
  </svelte:element>
{/snippet}

<dialog
  aria-labelledby="{modalId}-title"
  id={modalId}
  class="fr-modal before:h-[5vh]! before:basis-[5vh]! after:h-[5vh]! after:basis-[5vh]!"
  {...dsfrEvents}
>
  <div class="fr-container fr-container--fluid max-w-[1300px]!">
    <div class="fr-grid-row fr-grid-row--center">
      <div class="fr-col-12 fr-col-md-12 fr-col-lg-12">
        <div
          class="fr-modal__body bg-light-grey! lg:max-h-[90vh]! dark:border-grey! rounded-xl dark:border!"
          style="overscroll-behavior: contain;"
        >
          <div class="fr-modal__header pb-0!">
            <Button
              variant="tertiary-no-outline"
              text={m['words.close']()}
              title={m['closeModal']()}
              aria-controls={modalId}
              class="fr-btn--close"
            />
          </div>

          {#if model}
            <article class="fr-modal__content">
              <h1
                id="{modalId}-title"
                class="mb-7! text-lg! font-normal! text-dark-grey gap-2 flex items-center"
              >
                <AILogo logo={model.lab.logo} size="lg" alt={model.lab.name} />
                <div>
                  {model.lab.name}/<span class="font-extrabold">{model.name}</span>
                </div>
              </h1>

              <div class="gap-4 flex flex-col">
                <section class="gap-3 flex flex-col">
                  <h2 class="text-base! mb-0!">{m['models.technical.title']()}</h2>
                  <ul class="fr-badges-group">
                    {#each badges as badge, i (i)}
                      <li>
                        <Badge id="general-badge-{i}" {...badge} class="mb-0!" />
                      </li>
                    {/each}
                  </ul>

                  <div class="lg:grid-cols-24 gap-4 md:grid-cols-9 sm:grid-cols-2 grid">
                    {#each cards.technical as card, i (i)}
                      <InfoCard
                        {...card}
                        id="technical-{card.id}"
                        iconClass="text-info"
                        class={card.id === 'modalities'
                          ? 'md:col-span-2 lg:col-span-4'
                          : 'md:col-span-3 lg:col-span-5'}
                      >
                        {#if card.id === 'price'}
                          <div class="gap-2 flex w-full flex-col">
                            {#each card.contents as c, i (i)}
                              <div>
                                <p class="mb-0! font-bold text-[22px]!">
                                  ${@html sanitize(c.content)}
                                </p>
                                <p class="text-sm! text-grey mb-0!">
                                  {c.subContent}
                                </p>
                              </div>
                            {/each}
                          </div>
                        {:else if card.id === 'modalities'}
                          <div class="grid grid-cols-2 gap-[1px] bg-[#E0E0E0]">
                            {#each MODALITIES as mod (mod.id)}
                              {@const active = model.inputs.includes(mod.id)}
                              <div
                                class="bg-white p-2 text-xs gap-1 flex flex-col items-center"
                                aria-hidden={active ? 'false' : 'true'}
                              >
                                <Icon
                                  icon={mod.icon}
                                  size="sm"
                                  block
                                  class={active ? 'text-primary' : 'text-[#B3B3B3]'}
                                />
                                <span class={{ 'text-[#B3B3B3]': !active }}>{mod.title}</span>
                              </div>
                            {/each}
                          </div>
                        {:else}{/if}
                      </InfoCard>
                    {/each}
                  </div>
                </section>

                <div class="gap-4 xl:grid-cols-5 grid">
                  <section class="xl:col-span-3">
                    <h2 class="text-base! mb-3!">{m['models.envImpact.title']()}</h2>

                    <div class="gap-4 md:flex-row flex flex-col">
                      <article class="cg-border bg-white p-4 relative flex basis-1/2 flex-col">
                        {@render iconHeading({
                          icon: 'i-ri-cpu-line',
                          title: m['models.envImpact.hardware.title'](),
                          iconClass: 'text-grey'
                        })}

                        <Tooltip
                          id="hardware-tooltip"
                          text={m['models.envImpact.hardware.tooltip']()}
                          size="xs"
                          class="top-3 right-4 absolute"
                        />
                        {#if hardware}
                          <div class="my-6">
                            <Icon
                              icon={hardware.icon}
                              size="lg"
                              class="text-primary mb-3 block h-[44px]! w-[44px]!"
                              aria-label={m[
                                `models.envImpact.hardware.types.${hardware.tier}.name`
                              ]()}
                            />
                            <p class="font-bold mb-0!">
                              {m[`models.envImpact.hardware.types.${hardware.tier}.title`]({
                                count: hardware.gpuCount
                              })}
                            </p>
                            <p class="text-grey text-sm! mb-0!">
                              {m[`models.envImpact.hardware.types.${hardware.tier}.detail`]()}
                            </p>

                            <div
                              class="mt-7 gap-2 flex w-full items-start justify-between"
                              aria-hidden="true"
                            >
                              {#each hardwares as h, i (h.tier)}
                                {@const active = h.tier === hardware.tier}
                                <div class="gap-1.5 flex basis-1/4 flex-col items-center">
                                  <Icon
                                    icon={h.icon}
                                    size="lg"
                                    block
                                    class={active ? 'text-primary' : 'text-[#B3B3B3]'}
                                  />
                                  <span class="text-xs text-center" class:text-[#B3B3B3]={!active}>
                                    {m[`models.envImpact.hardware.types.${h.tier}.name`]()}
                                  </span>
                                </div>
                                {#if i < 3}
                                  <Icon
                                    icon="i-ri-arrow-right-s-line"
                                    size="lg"
                                    class="mt-1 text-[#B3B3B3]"
                                    block
                                  />
                                {/if}
                              {/each}
                            </div>
                          </div>
                        {/if}
                      </article>
                      {#if cards.energy}
                        <InfoCard {...cards.energy} class="basis-1/2 justify-between">
                          <div
                            class="gap-1 my-6 flex w-full flex-col"
                            aria-label="{m['models.cards.energy.title_md']()} {model.energy_class}"
                          >
                            {#each energyRows as row (row.letter)}
                              {@const active = row.letter === model.energy_class}
                              <div class="text-sm font-bold text-white h-7 flex items-center">
                                <div class="w-9/10">
                                  <div
                                    class="ps-2 h-7 flex items-center justify-start"
                                    style="background-color: var({row.color}); width: {row.width}%; clip-path: polygon(0 0, calc(100% - 12px) 0, 100% 50%, calc(100% - 12px) 100%, 0 100%);"
                                    class:opacity-30={!active}
                                  >
                                    {row.letter}
                                  </div>
                                </div>
                                {#if active}
                                  <div
                                    class="rounded-sm h-7 w-7 ms-auto flex items-center justify-center leading-none"
                                    style="background-color: var({row.color});"
                                  >
                                    <span class="">
                                      {row.letter}
                                    </span>
                                  </div>
                                {/if}
                              </div>
                            {/each}
                          </div>
                        </InfoCard>
                      {/if}
                    </div>
                  </section>

                  <section class="xl:col-span-2 flex w-full flex-col">
                    <h2 class="text-base! mb-3!">{m['models.opennessSovereignty.title']()}</h2>

                    <div class="cg-border bg-white p-4 h-full">
                      <dl class="p-0">
                        {#each sovFields as field (field.id)}
                          <div
                            class="min-h-9 py-1.5 gap-3 flex items-center border-[--grey-925-125] not-last:border-b"
                          >
                            <dt class="p-0 text-grey text-xs">
                              {m[`models.opennessSovereignty.fields.${field.id}`]()}
                            </dt>
                            <dd class="p-0 text-sm font-bold ms-auto text-right">
                              {#if field.id === 'license_type'}
                                <Badge {...field.value} size="sm" />
                              {:else if field.id === 'license_name'}
                                {field.value}
                              {:else if field.id === 'origin_country'}
                                <!-- FIXME flag -->
                                {field.value.toUpperCase()}
                              {:else}
                                {@const words =
                                  field.id === 'eu_hostable'
                                    ? (['yes', 'no'] as const)
                                    : field.id === 'reuse' || field.id === 'commercial_use'
                                      ? (['allowed', 'forbidden'] as const)
                                      : (['public', 'private'] as const)}
                                <span class={field.value ? 'text-success' : 'text-error'}>
                                  {m[`words.${field.value ? words[0] : words[1]}`]()}
                                </span>
                              {/if}
                            </dd>
                          </div>
                        {/each}
                      </dl>
                    </div>
                  </section>
                </div>

                <div class="gap-4 xl:grid-cols-5 grid">
                  {#if model.data && cards.rank}
                    <section class="xl:col-span-3">
                      <h2 class="text-base! mb-3!">{m['models.performance.title']()}</h2>

                      <div class="cg-border bg-white p-4 gap-5 relative flex flex-col">
                        <Tooltip
                          id="perf-tooltip"
                          text={m['models.performance.tooltip']()}
                          size="xs"
                          class="top-3 right-4 absolute"
                        />
                        <dl class="md:gap-15 p-0 gap-5 md:flex-row flex flex-col">
                          <div>
                            {@render iconHeading({
                              tag: 'dt',
                              icon: 'i-ri-thumb-up-line',
                              title: m['models.performance.fields.votes.title']()
                            })}

                            <dd class="p-0 mb-0! font-bold text-[22px]!">
                              {model.data.n_match}
                            </dd>
                          </div>

                          <div>
                            {@render iconHeading({
                              tag: 'dt',
                              icon: 'i-ri-equalizer-2-line',
                              title: m['models.performance.fields.score.title']()
                            })}

                            <dd class="p-0 mb-0! font-bold text-[20px]!">
                              {model.data.elo}
                              {#if model.data.trust_range}
                                <span class="text-grey text-xs! font-normal">
                                  {m['models.performance.fields.score.detail']({
                                    count: `-${model.data.trust_range[1]}/+${model.data.trust_range[0]}`
                                  })}
                                </span>
                              {/if}
                            </dd>
                          </div>

                          <div>
                            {@render iconHeading({
                              tag: 'dt',
                              icon: cards.rank.icon,
                              title: cards.rank.title,
                              iconClass: 'text-yellow'
                            })}

                            <dd class="p-0 mb-0! font-bold text-[20px]!">
                              {cards.rank.content}<span class="text-grey font-normal text-xs!">
                                {m['models.cards.rank.detail']({
                                  count: commons.modelsCount
                                })}
                              </span>
                            </dd>
                          </div>
                        </dl>

                        <div
                          class="bg-very-light-primary py-2 px-4 b-light-primary rounded-sm flex flex-col items-center border"
                        >
                          <div
                            class="h-4 from-primary mt-4 w-full rounded-full bg-linear-to-r to-[#AA5050]"
                          ></div>
                          <div
                            class="gap-2 flex w-9/10 justify-between"
                            aria-label={m['models.performance.level']({
                              count: model.data.rankClass,
                              total: rankingRows.length
                            })}
                          >
                            {#each rankingRows as row (row.c)}
                              {@const active = row.c === model.data.rankClass}
                              <div class="gap-2 -mt-9 flex flex-col items-center">
                                <Icon
                                  icon="i-ri-triangle-fill"
                                  class={['text-primary -scale-100', { invisible: !active }]}
                                />
                                <div class="h-2 w-2 bg-white rounded-full"></div>

                                <div class="lh-normal! text-center">
                                  <div class="text-lg">{row.emoji}</div>
                                  <div class="text-xs font-bold" class:opacity-50={!active}>
                                    {m['models.performance.group']({ count: row.c })}<br />
                                  </div>
                                  <div class="text-xxs" class:opacity-50={!active}>
                                    {m['models.performance.rankFromTo'](
                                      commons.rankingTiers[row.c]
                                    )}
                                  </div>
                                </div>
                              </div>
                            {/each}
                          </div>
                        </div>
                      </div>
                    </section>
                  {/if}

                  {#if model.links?.length}
                    <section class="xl:col-span-2">
                      <h2 class="text-base! mb-3!">{m['models.infosSources.title']()}</h2>

                      <div class="cg-border bg-white p-4">
                        <ul class="p-0 m-0 grid w-full grid-cols-2">
                          {#each model.links as link (link.url)}
                            <li class="list-none">
                              <Link href={link.url} text={link.text} class="inline" />
                            </li>
                          {/each}
                        </ul>
                      </div>
                    </section>
                  {/if}
                </div>
              </div>
            </article>
          {/if}
        </div>
      </div>
    </div>
  </div>
</dialog>
