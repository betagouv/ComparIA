<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Button, Icon } from '$components/dsfr'
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
              badge: model.licenseInfos.commercialUseSpecificities
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
            badge: model.licenseInfos.reuseSpecificities
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

<dialog
  aria-labelledby="{modalId}-title"
  id={modalId}
  class="fr-modal before:h-[5vh]! before:basis-[5vh]! after:h-[5vh]! after:basis-[5vh]!"
>
  <div class="fr-container fr-container--fluid">
    <div class="fr-grid-row fr-grid-row--center">
      <div class="fr-col-12 fr-col-md-12 fr-col-lg-12">
        <div
          class="fr-modal__body bg-light-grey! dark:border-grey! rounded-xl lg:max-h-[90vh]! dark:border!"
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
            <div class="fr-modal__content">
              <h5
                id="{modalId}-title"
                class="text-dark-grey mb-3! flex items-center gap-2 text-lg! font-normal!"
              >
                <AILogo iconPath={model.icon_path} size="lg" alt={model.organisation} />
                <div>
                  {model.organisation}/<span class="font-extrabold">{model.simple_name}</span>
                </div>
              </h5>

              <ul class="fr-badges-group mb-4!">
                {#each badges as badge, i (i)}
                  <li><Badge id="general-badge-{i}" {...badge} /></li>
                {/each}
              </ul>

              {@html sanitize(model.desc).replaceAll('<p>', '<p class="last:mb-5!">')}

              <div class="grid gap-5 lg:grid-cols-8">
                <div class="cg-border bg-white p-4 pb-6 lg:col-span-4">
                  <div class="mb-4 flex">
                    <h6 class="mb-0! flex text-lg!">
                      <Icon icon="ruler" block class="text-info me-2" />
                      {m['models.size.title']()}
                    </h6>
                    <Badge {...model.badges.size} size="sm" class="ms-auto self-center!" />
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
                    <h6 class="mb-0! flex text-lg!">
                      <Icon icon="lightbulb-line" block class="text-yellow me-2" />
                      {m['models.arch.title']()}
                    </h6>
                    <Badge
                      {...model.badges.arch}
                      id={modalId + '-arch'}
                      size="sm"
                      class="ms-auto self-center!"
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
                      <h6 class="mb-0! flex text-sm!">
                        <Icon icon="copyright-line" block class="me-2" />
                        {m['models.conditions.title']()}
                      </h6>
                      <Badge {...model.badges.licenseName} size="sm" class="ms-auto self-center!" />
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
                      'grid gap-4 text-xs!',
                      licenseCards.length > 1 ? 'col-span-1 grid-cols-2' : ''
                    ]}
                  >
                    {#each licenseCards as card, i (i)}
                      <div
                        class={[
                          'cg-border flex w-full flex-col items-center p-3 text-center',
                          { 'justify-between': !!card.subtitle }
                        ]}
                      >
                        <p class="mb-3! text-xs! font-bold">{card.title}</p>

                        <Badge {...card.badge} size="sm" />
                        {#if !!card.subtitle}
                          <p class="mt-3! mb-0! text-xs!">{card.subtitle}</p>
                        {/if}
                      </div>
                    {/each}
                  </div>
                </div>

                <div class="cg-border bg-white p-4 pb-6 lg:col-span-2">
                  <h6 class="mb-2! flex text-sm!">
                    <Icon icon="link" block class="me-2" />
                    {m['models.extra.title']()}
                  </h6>

                  <p class="text-grey mb-3! text-xs!">
                    {@html sanitize(
                      m[
                        `models.extra.experts.${model.distribution === 'api-only' ? 'api-only' : 'open-weights'}`
                      ]({
                        linkProps: externalLinkProps(model.url || '#')
                      })
                    )}
                  </p>
                  <p class="text-grey mb-0! text-xs!">
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
