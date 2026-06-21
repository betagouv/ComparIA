<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Button, Icon, Link, Tooltip } from '$components/dsfr'
  import { ENERGY_CLASSES } from '$lib/generated/constants'
  import { m } from '$lib/i18n/messages'
  import type { BotModel, Commons } from '$lib/models'
  import { ENERGY_CLASS_COLORS, isMaybeArch } from '$lib/models'
  import { propsToAttrs, sanitize } from '$lib/utils/commons'
  import type { ClassValue } from 'svelte/elements'

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
  const technicalCards = $derived.by(() => {
    if (!model) return []
    const midProps = propsToAttrs({ class: 'text-base!' })
    const smallProps = propsToAttrs({ class: 'text-sm!' })
    const cards = [
      {
        id: 'size',
        icon: 'i-ri-ruler-line',
        content: m['models.technical.size.params_count']({
          count: model.params,
          midProps,
          smallProps
        }),
        subContent:
          model.license.kind === 'proprietary'
            ? m['models.technical.size.estimated']()
            : model.active_params
              ? m['models.technical.size.active_params_count']({ count: model.active_params })
              : undefined,
        desc: m['models.technical.size.desc']()
      } as const,
      {
        id: 'arch',
        icon: 'i-ri-stack-line',
        tooltip: m['models.technical.arch.tooltip'](),
        content: m[`generated.archs.${isMaybeArch(model.arch) ? 'na' : model.arch}.name`](),
        subContent: model.arch === 'moe' ? m['generated.archs.moe.title']() : undefined,
        desc: m[`generated.archs.${isMaybeArch(model.arch) ? 'na' : model.arch}.desc`]()
      } as const,
      {
        id: 'context',
        icon: 'i-ri-text-snippet',
        tooltip: m['models.technical.context.tooltip'](),
        content: m['models.technical.context.tokens_count']({
          count: model.context_tokens ? Math.floor(model.context_tokens / 1000) : 'FIXME',
          midProps,
          smallProps
        }),
        subContent: m['models.technical.context.chars_count']({
          count: model.context_tokens ? Math.floor((model.context_tokens * 4) / 1000) : 'FIXME'
        }),
        desc: 'FIXME'
      } as const,
      {
        id: 'price',
        icon: 'i-ri-price-tag-3-line',
        desc: m['models.technical.price.desc'](),
        content: [
          {
            content: m['models.technical.price.price_count']({
              count: model.price_in.toFixed(2),
              midProps
            }),
            subContent: m['models.technical.price.price_in']()
          },
          {
            content: m['models.technical.price.price_count']({
              count: model.price_out.toFixed(2),
              midProps
            }),
            subContent: m['models.technical.price.price_out']()
          }
        ]
      } as const,
      {
        id: 'modalities',
        icon: 'i-ri-shapes-line'
      } as const
    ]
    return cards.map((card) => ({
      ...card,
      title: m[`models.technical.${card.id}.title`]()
    }))
  })

  const sovFields = $derived.by(() => {
    if (!model) return []
    return [
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

<button class="hidden" data-fr-opened={!!model} aria-controls={modalId}>Hidden</button>

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
                        <Badge id="general-badge-{i}" {...badge} variant="yellow" class="mb-0!" />
                      </li>
                    {/each}
                  </ul>

                  <div class="xl:grid-cols-5 gap-4 md:grid-cols-3 sm:grid-cols-2 grid">
                    {#each technicalCards as card, i (i)}
                      <article class="cg-border bg-white p-4">
                        <div class="flex">
                          {@render iconHeading({ ...card, classes: 'mb-2!' })}

                          <div class="ms-auto">
                            {#if card.id === 'size'}
                              <Badge {...model.badges.size} size="sm" />
                            {:else if card.tooltip}
                              <Tooltip id="technical-tooltip-{card.id}" size="xs">
                                {@html sanitize(card.tooltip)}
                              </Tooltip>
                            {/if}
                          </div>
                        </div>

                        {#if card.id === 'modalities'}
                          FIXME
                        {:else if card.id === 'price'}
                          <div class="flex w-full">
                            {#each card.content as c, i (i)}
                              <div class="basis-1/2">
                                <p class="mb-0! font-bold text-[22px]!">
                                  ${@html sanitize(c.content)}
                                </p>
                                <p class="text-sm! text-grey mb-0!">
                                  {c.subContent}
                                </p>
                              </div>
                            {/each}
                          </div>
                        {:else}
                          <p class="mb-0! font-bold text-[22px]!">
                            {@html sanitize(card.content)}
                          </p>
                          {#if card.subContent}
                            <p class="text-sm! text-grey mb-0! ù">
                              {card.subContent}
                            </p>
                          {/if}
                        {/if}

                        {#if card.desc}
                          <p
                            class="bg-very-light-primary text-xxs p-1 mb-0! mt-3 b-light-primary rounded-sm border"
                          >
                            {card.desc}
                          </p>
                        {/if}
                      </article>
                    {/each}
                  </div>
                </section>

                <div class="gap-4 xl:grid-cols-5 grid">
                  <section class="col-span-3">
                    <h2 class="text-base! mb-3!">{m['models.envImpact.title']()}</h2>

                    <div class="gap-4 md:flex-row flex flex-col">
                      <article
                        class="cg-border bg-white p-4 relative flex basis-1/2 flex-col justify-between"
                      >
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

                            <div class="mt-7 flex w-full justify-between" aria-hidden="true">
                              {#each hardwares as h, i (h.tier)}
                                {@const active = h.tier === hardware.tier}
                                <div class="gap-1 flex basis-1/4 flex-col items-center">
                                  <Icon
                                    icon={h.icon}
                                    size="md"
                                    block
                                    class={active ? 'text-primary' : 'text-[#B3B3B3]'}
                                  />
                                  <span class="text-xxs text-center" class:text-[#B3B3B3]={!active}>
                                    {m[`models.envImpact.hardware.types.${h.tier}.name`]()}
                                  </span>
                                </div>
                                {#if i < 3}
                                  <Icon
                                    icon="i-ri-arrow-right-s-line"
                                    size="md"
                                    class="text-[#B3B3B3]"
                                    block
                                  />
                                {/if}
                              {/each}
                            </div>
                          </div>

                          <p
                            class="bg-very-light-primary text-xxs p-1 mb-0! b-light-primary rounded-sm border"
                          >
                            FIXME
                          </p>
                        {/if}
                      </article>

                      <article
                        class="cg-border bg-white p-4 relative flex basis-1/2 flex-col justify-between"
                      >
                        {@render iconHeading({
                          icon: 'i-ri-leaf-line',
                          title: m['models.envImpact.conso.title'](),
                          iconClass: 'text-success'
                        })}

                        <Tooltip
                          id="conso-tooltip"
                          text={m['models.envImpact.conso.tooltip']()}
                          size="xs"
                          class="top-3 right-4 absolute"
                        />

                        <div
                          class="gap-2 my-6 flex w-full flex-col"
                          aria-label="{m['models.envImpact.conso.title']()} {model.energy_class}"
                        >
                          {#each energyRows as row (row.letter)}
                            {@const active = row.letter === model.energy_class}
                            <div class="text-sm font-bold text-white flex h-[23px] items-center">
                              <div class="w-9/10">
                                <div
                                  class="ps-2 flex h-full items-center justify-start"
                                  style="background-color: {row.color}; width: {row.width}%; clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 50%, calc(100% - 10px) 100%, 0 100%);"
                                  class:opacity-30={!active}
                                >
                                  {row.letter}
                                </div>
                              </div>
                              {#if active}
                                <div
                                  class="rounded-sm bg-primary ms-auto flex h-full w-[23px] items-center justify-center leading-none"
                                >
                                  <span class="">
                                    {row.letter}
                                  </span>
                                </div>
                              {/if}
                            </div>
                          {/each}
                        </div>

                        <p
                          class="bg-very-light-primary text-xxs p-1 mb-0! b-light-primary rounded-sm border"
                        >
                          FIXME
                        </p>
                      </article>
                    </div>
                  </section>

                  <section class="col-span-2 flex flex-col">
                    <h2 class="text-base! mb-3!">{m['models.opennessSovereignty.title']()}</h2>

                    <div class="cg-border bg-white p-4 h-full">
                      <dl class="p-0">
                        {#each sovFields as field (field.id)}
                          <div class="py-1 flex border-[--grey-925-125] not-last:border-b">
                            <dt class="p-0 text-grey text-xs">
                              {m[`models.opennessSovereignty.fields.${field.id}`]()}
                            </dt>
                            <dd class="p-0 text-sm font-bold ms-auto">
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
                  <section class="col-span-3">
                    <h2 class="text-base! mb-3!">{m['models.performance.title']()}</h2>

                    <div class="cg-border bg-white p-4 gap-5 relative flex flex-col">
                      <Tooltip
                        id="perf-tooltip"
                        text={m['models.performance.tooltip']()}
                        size="xs"
                        class="top-3 right-4 absolute"
                      />
                      {#if model.data}
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
                              <span class="text-grey text-xs! font-normal">
                                {m['models.performance.fields.score.detail']({
                                  count: 'FIXME'
                                })}
                              </span>
                            </dd>
                          </div>

                          <div>
                            {@render iconHeading({
                              tag: 'dt',
                              icon: 'i-ri-trophy-line',
                              title: m['models.performance.fields.rank.title'](),
                              iconClass: 'text-yellow'
                            })}

                            <dd class="p-0 mb-0! font-bold text-[20px]!">
                              {m['models.performance.fields.rank.to'](
                                commons.rankingTiers[model.data.rankClass]
                              )}<span class="text-grey font-normal text-xs!">
                                {m['models.performance.fields.rank.detail']({
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
                      {/if}
                    </div>
                  </section>

                  {#if model.links?.length}
                    <section class="col-span-2">
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
