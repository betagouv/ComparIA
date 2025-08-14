<script lang="ts">
  import { Badge } from '$lib/components/dsfr'
  import Icon from '$lib/components/Icon.svelte'
  import Tooltip from '$lib/components/Tooltip.svelte'
  import { m } from '$lib/i18n/messages'
  import { isAvailableLicense, licenseAttrs, type APIBotModel } from '$lib/models'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'

  let { model: modelData, modalId }: { model?: APIBotModel; modalId: string } = $props()

  const model = $derived.by(() => {
    if (!modelData) return
    return {
      ...modelData,
      licenseDesc: isAvailableLicense(modelData.license)
        ? m[`models.licenses.descriptions.${modelData.license}`]()
        : m['models.licenses.noDesc'](),
      warningCommercial: licenseAttrs?.[modelData.license]?.warningCommercial,
      prohibitCommercial: licenseAttrs?.[modelData.license]?.prohibitCommercial
    }
  })

  const badges = $derived.by(() => {
    if (!modelData) return []
    return [
      modelData.fully_open_source
        ? ({
            variant: 'green',
            text: m['models.licenses.type.openSource'](),
            tooltip: m['models.openWeight.tooltips.openSource']()
          } as const)
        : modelData.distribution === 'open-weights'
          ? ({
              variant: 'yellow',
              text: m['models.licenses.type.semiOpen'](),
              tooltip: m['models.openWeight.tooltips.openWeight']()
            } as const)
          : ({ variant: 'orange', text: m['models.licenses.type.proprietary']() } as const),
      modelData.release_date
        ? ({ color: '', text: m['models.release']({ date: modelData.release_date }) } as const)
        : null,
      modelData?.reasoning ? ({ variant: '', text: 'Modèle de raisonnement' } as const) : null
    ].filter((b) => !!b)
  })

  const sizeBadge = $derived.by(() => {
    if (!modelData) return
    return {
      id: 'model-parameters',
      variant: 'info',
      text:
        modelData.distribution === 'api-only'
          ? m['models.size.estimated']({ size: modelData.friendly_size })
          : m['models.parameters']({ number: modelData.params }),
      tooltip:
        modelData.distribution === 'api-only' ? m['models.openWeight.tooltips.params']() : undefined
    } as const
  })
</script>

<dialog aria-labelledby="{modalId}-title" id={modalId} class="fr-modal">
  <div class="fr-container fr-container--fluid">
    <div class="fr-grid-row fr-grid-row--center">
      <div class="fr-col-12 fr-col-md-10 fr-col-lg-10">
        <div class="fr-modal__body bg-light-grey! rounded-xl">
          <div class="fr-modal__header pb-0!">
            <button
              class="fr-btn--close fr-btn"
              title="Fermer la fenêtre modale"
              aria-controls={modalId}
            >
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
                  src="/orgs/{model.icon_path}"
                  alt="{model.organisation} logo"
                />
                <div>
                  {model.organisation}/<span class="font-extrabold">{model.simple_name}</span>
                </div>
              </h5>

              <ul class="fr-badges-group mb-4!">
                {#each badges as badge, i}
                  <li><Badge {...badge} id="general-badge-{i}" /></li>
                {/each}
              </ul>

              <p class="mb-5!">{model.description}</p>

              <div class="grid gap-5 lg:grid-cols-8">
                <div class="cg-border bg-white p-4 pb-6 lg:col-span-4">
                  <div class="mb-4 flex">
                    <h6 class="mb-0! text-lg! flex">
                      <Icon icon="ruler" block class="text-info me-2" />{m['models.size.title']()}
                    </h6>
                    <Badge {...sizeBadge!} size="sm" class="self-center! ms-auto" />
                  </div>

                  <p class="text-sm! mb-0! fr-message">
                    {m[`models.size.descriptions.${model.friendly_size}`]()}
                  </p>
                </div>

                <div class="cg-border bg-white p-4 pb-6 lg:col-span-4">
                  <div class="mb-4 flex">
                    <h6 class="mb-0! text-lg! flex">
                      <Icon icon="lightbulb-line" block class="text-yellow me-2" />Le saviez-vous ?
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

                  <p class="text-sm! mb-0! fr-message">arch desc</p>
                </div>

                <div class="cg-border flex gap-3 bg-white p-4 pb-6 lg:col-span-6">
                  <div>
                    <div class="mb-2 flex flex-wrap gap-2">
                      <h6 class="mb-0! text-sm! flex">
                        <Icon icon="copyright-line" block class="me-2" />{m['models.conditions']()}
                      </h6>
                      <Badge id="license-badge" size="sm" class="self-center! ms-auto">
                        {#if model.distribution === 'open-weights'}
                          {m['models.licenses.name']({ licence: model.license })}
                        {:else}
                          {m['models.licenses.commercial']()}
                        {/if}
                      </Badge>
                    </div>

                    <p class="mb-0! text-xs! fr-message">{model.licenseDesc}</p>
                  </div>

                  <div class="text-xs!">
                    <!-- FIXME -->
                    <!-- <div class="cg-border p-2"></div>
                    <div class="cg-border p-2"></div> -->
                  </div>
                </div>

                <div class="cg-border bg-white p-4 pb-6 lg:col-span-2">
                  <h6 class="text-sm! mb-2! flex">
                    <Icon icon="link" block class="me-2" />Pour aller plus loin
                  </h6>

                  <p class="text-grey text-xs! mb-3!">
                    {@html sanitize(
                      m[`models.extra.experts.${model.distribution}`]({
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
