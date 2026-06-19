<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Button, Icon, Tooltip } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { isMaybeArch, type BotModel } from '$lib/models'
  import { propsToAttrs, sanitize } from '$lib/utils/commons'

  let { model, modalId, onClose }: { model?: BotModel; modalId: string; onClose?: () => void } =
    $props()

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
</script>

<button class="hidden" data-fr-opened={!!model} aria-controls={modalId}>Hidden</button>

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
                      <article class="cg-border bg-white p-4 relative">
                        <div class="flex">
                          <h2 class="text-sm gap-1 font-normal mb-2! flex items-center">
                            <Icon icon={card.icon} size="xs" block class="text-info" />
                            {card.title}
                          </h2>
                          {#if card.id === 'size'}
                            <Badge {...model.badges.size} size="sm" class="ms-auto self-center!" />
                          {/if}
                        </div>

                        {#if card.tooltip}
                          <Tooltip
                            id="technical-tooltip-{card.id}"
                            size="xs"
                            class="top-3 right-4 absolute"
                          >
                            {@html sanitize(card.tooltip)}
                          </Tooltip>
                        {/if}

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

                <div class="gap-4 flex">
                  <section class="basis-3/5">
                    <h2 class="text-base! mb-3!">{m['models.envImpact.title']()}</h2>

                    <div class="gap-4 flex">
                      <article class="cg-border bg-white p-4 relative basis-1/2">
                        <h2 class="text-sm gap-1 font-normal mb-2! flex items-center">
                          <Icon icon="i-ri-cpu-line" size="xs" block class="text-grey" />
                          {m['models.envImpact.hardware.title']()}
                        </h2>

                        <Tooltip
                          id="hardware-tooltip"
                          text={m['models.envImpact.hardware.tooltip']()}
                          size="xs"
                          class="top-3 right-4 absolute"
                        />
                      </article>

                      <article class="cg-border bg-white p-4 relative basis-1/2">
                        <h2 class="text-sm gap-1 font-normal mb-2! flex items-center">
                          <Icon icon="i-ri-leaf-line" size="xs" block class="text-success" />
                          {m['models.envImpact.conso.title']()}
                        </h2>

                        <Tooltip
                          id="conso-tooltip"
                          text={m['models.envImpact.conso.tooltip']()}
                          size="xs"
                          class="top-3 right-4 absolute"
                        />
                      </article>
                    </div>
                  </section>

                  <section class="basis-2/5">
                    <h2 class="text-base! mb-3!">{m['models.opennessSovereignty.title']()}</h2>

                    <div class="cg-border bg-white p-4"></div>
                  </section>
                </div>

                <div class="gap-4 flex">
                  <section class="basis-3/5">
                    <h2 class="text-base! mb-3!">{m['models.performance.title']()}</h2>

                    <div class="cg-border bg-white p-4"></div>
                  </section>

                  <section class="basis-2/5">
                    <h2 class="text-base! mb-3!">{m['models.infosSources.title']()}</h2>

                    <div class="cg-border bg-white p-4"></div>
                  </section>
                </div>
              </div>
            </article>
          {/if}
        </div>
      </div>
    </div>
  </div>
</dialog>
