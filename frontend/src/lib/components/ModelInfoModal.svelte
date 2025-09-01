<script lang="ts">
  import { Badge, Icon } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import type { BotModel } from '$lib/models'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'

  let { model, modalId }: { model?: BotModel; modalId: string } = $props()

  const badges = $derived.by(() => {
    if (!model) return []
    const { license, releaseDate, reasoning } = model.badges
    return [license, releaseDate, reasoning].filter((b) => !!b)
  })

  const licenseCards = $derived.by(() => {
    if (!model) return []
    return [
      model.commercial_use === null
        ? null
        : !model.commercial_use
          ? {
              title: m['models.conditions.commercialUse.question'](),
              badge: { variant: 'red' as const, text: m['models.conditions.types.forbidden']() }
            }
          : {
              title: m['models.conditions.commercialUse.title'](),
              badge: !!model.licenseInfos.commercialUseSpecificities
                ? {
                    variant: 'purple' as const,
                    text: m['models.conditions.types.conditions']()
                  }
                : { variant: 'green' as const, text: m['models.conditions.types.allowed']() },
              subtitle: model.licenseInfos.commercialUseSpecificities
            },
      !model.reuse
        ? {
            title: m['models.conditions.reuse.question'](),
            badge: { variant: 'red' as const, text: m['models.conditions.types.forbidden']() },
            subtitle: m['models.conditions.reuse.subTitle']()
          }
        : {
            title: m['models.conditions.reuse.title'](),
            badge: !!model.licenseInfos.reuseSpecificities
              ? {
                  variant: 'purple' as const,
                  text: m['models.conditions.types.conditions']()
                }
              : { variant: 'green' as const, text: m['models.conditions.types.allowed']() },
            subtitle: model.licenseInfos.reuseSpecificities
          }
    ].filter((b) => !!b)
  })
</script>

<dialog aria-labelledby="{modalId}-title" id={modalId} class="fr-modal">
  <div class="fr-container fr-container--fluid">
    <div class="fr-grid-row fr-grid-row--center">
      <div class="fr-col-12 fr-col-md-12 fr-col-lg-12">
        <div class="fr-modal__body bg-light-grey! dark:border! dark:border-grey! rounded-xl">
          <div class="fr-modal__header pb-0!">
            <button class="fr-btn--close fr-btn" title={m['closeModal']()} aria-controls={modalId}>
              {m['words.close']()}
            </button>
          </div>

          {#if model}
            <div class="fr-modal__content">
              <h5
                id="{modalId}-title"
                class="text-dark-grey font-normal! text-lg! mb-3! flex items-center gap-2"
              >
                <img
                  class="h-[34px] object-contain"
                  src="/orgs/ai/{model.icon_path}"
                  alt="{model.organisation} logo"
                />
                <div>
                  {model.organisation}/<span class="font-extrabold">{model.simple_name}</span>
                </div>
              </h5>

              <ul class="fr-badges-group mb-4!">
                {#each badges as badge, i}
                  <li><Badge id="general-badge-{i}" {...badge} /></li>
                {/each}
              </ul>

              {@html sanitize(model.desc).replaceAll('<p>', '<p class="last:mb-5!">')}

              <div class="grid gap-5 lg:grid-cols-8">
                <div class="cg-border bg-white p-4 pb-6 lg:col-span-4">
                  <div class="mb-4 flex">
                    <h6 class="mb-0! text-lg! flex">
                      <Icon icon="ruler" block class="text-info me-2" />{m['models.size.title']()}
                    </h6>
                    <Badge {...model.badges.size} size="sm" class="self-center! ms-auto" />
                  </div>

                  <div class="fr-message block!">
                    {@html sanitize(model.sizeDesc).replaceAll(
                      '<p>',
                      '<p class="text-sm! mb-3! last:mb-0!">'
                    )}
                  </div>
                </div>

                <div class="cg-border bg-white p-4 pb-6 lg:col-span-4">
                  <div class="mb-4 flex">
                    <h6 class="mb-0! text-lg! flex">
                      <Icon icon="lightbulb-line" block class="text-yellow me-2" />{m[
                        'models.arch.title'
                      ]()}
                    </h6>
                    <!-- FIXME -->
                    <Badge
                      id="arch-badge"
                      variant="yellow"
                      text="arch"
                      tooltip="arch"
                      size="sm"
                      class="self-center! ms-auto"
                    />
                  </div>

                  <div class="fr-message block!">
                    {@html sanitize(model.fyi).replaceAll(
                      '<p>',
                      '<p class="text-sm! mb-3! last:mb-0!">'
                    )}
                  </div>
                </div>

                <div
                  class={[
                    'cg-border grid gap-4 bg-white p-4 pb-6 lg:col-span-6',
                    licenseCards.length > 1 ? 'md:grid-cols-2' : 'md:grid-cols-3'
                  ]}
                >
                  <div class={[licenseCards.length > 1 ? '' : 'col-span-2']}>
                    <div class="mb-2 flex flex-wrap gap-2">
                      <h6 class="mb-0! text-sm! flex">
                        <Icon icon="copyright-line" block class="me-2" />{m['models.conditions']()}
                      </h6>
                      <Badge {...model.badges.licenseName} size="sm" class="self-center! ms-auto" />
                    </div>

                    <div class="fr-message block!">
                      {@html sanitize(model.licenseInfos.desc).replaceAll(
                        '<p>',
                        '<p class="text-xs! mb-3! last:mb-0!">'
                      )}
                    </div>
                  </div>

                  <div
                    class={[
                      'text-xs! grid gap-4',
                      licenseCards.length > 1 ? 'col-span-1 grid-cols-2' : ''
                    ]}
                  >
                    {#each licenseCards as card}
                      <div
                        class={[
                          'cg-border flex w-full flex-col items-center p-3 text-center',
                          { 'justify-between': !!card.subtitle }
                        ]}
                      >
                        <p class="text-xs! mb-3! font-bold">{card.title}</p>

                        <Badge {...card.badge} size="sm" />
                        {#if !!card.subtitle}
                          <p class="text-xs! mb-0! mt-3!">{card.subtitle}</p>
                        {/if}
                      </div>
                    {/each}
                  </div>
                </div>

                <div class="cg-border bg-white p-4 pb-6 lg:col-span-2">
                  <h6 class="text-sm! mb-2! flex">
                    <Icon icon="link" block class="me-2" />{m['models.extra.title']()}
                  </h6>

                  <p class="text-grey text-xs! mb-3!">
                    {@html sanitize(
                      m[
                        `models.extra.experts.${model.distribution === 'api-only' ? 'api-only' : 'open-weights'}`
                      ]({
                        linkProps: externalLinkProps(model.url || '#')
                      })
                    )}
                  </p>
                  <p class="text-grey text-xs! mb-0!">
                    {@html sanitize(
                      m['models.extra.impacts']({
                        linkProps1: externalLinkProps(
                          'https://huggingface.co/spaces/genai-impact/ecologits-calculator'
                        ),
                        linkProps2: externalLinkProps('https://impactco2.fr')
                      })
                    )}
                  </p>
                </div>
              </div>
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
</dialog>
