<script lang="ts">
  import type { RevealData } from '$lib/chatService.svelte'
  import Icon from '$lib/components/Icon.svelte'
  import { m } from '$lib/i18n/messages'
  import type { APIBotModel } from '$lib/models'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'

  let {
    model,
    infos
  }: { model: APIBotModel; infos: Pick<RevealData, 'sizeDesc' | 'licenseDesc' | 'licenseAttrs'> } =
    $props()
</script>

<dialog
  aria-labelledby="fr-modal-title-modal-{model.id}"
  role="dialog"
  id="fr-modal-{model.id}"
  class="fr-modal"
>
  <div class="fr-container fr-container--fluid fr-container-md">
    <div class="fr-grid-row fr-grid-row--center">
      <div class="fr-col-12 fr-col-md-8">
        <div class="fr-modal__body">
          <div class="fr-modal__header">
            <button
              class="fr-btn--close fr-btn"
              title="Fermer la fenêtre modale"
              aria-controls="fr-modal-{model.id}"
            >
              {m['words.close']()}
            </button>
          </div>
          <div class="fr-modal__content fr-mb-4w modal-model">
            <h6 class="fr-mb-2w github-title">
              <img class="fr-mt-n2v relative inline" src="/orgs/{model.icon_path}" width="34" />
              {model.organisation}/<strong>{model.simple_name}</strong>
            </h6>
            <p class="fr-mb-4w">
              {#if model.fully_open_source}
                <span
                  class="fr-badge fr-badge--sm fr-badge--green-emeraude fr-badge--no-icon fr-mr-1v fr-mb-1v"
                >
                  {m['models.licenses.type.openSource']()}&nbsp;
                  <a
                    class="fr-icon fr-icon--xs fr-icon-question-line"
                    aria-describedby="license-{model.id}"
                  ></a>
                </span>
              {:else if model.distribution === 'open-weights'}
                <span
                  class="fr-badge fr-badge--yellow-tournesol fr-badge--no-icon fr-mr-1v fr-mb-1v"
                >
                  {m['models.licenses.type.semiOpen']()}&nbsp;
                  <a
                    class="fr-icon fr-icon--xs fr-icon-question-line"
                    aria-describedby="license-{model.id}"
                  ></a>
                </span>
              {:else}
                <span
                  class="fr-badge fr-badge--orange-terre-battue fr-badge--no-icon fr-mr-1v fr-mb-1v"
                >
                  {m['models.licenses.type.proprietary']()}
                </span>
              {/if}
              <span class="fr-badge fr-badge--info fr-badge--no-icon fr-mr-1v fr-mb-1v">
                {#if model.distribution === 'api-only'}
                  {m['models.size.estimated']({ size: model.friendly_size })}
                {:else}
                  {m['models.parameters']({ number: model.params })}&nbsp;<a
                    class="fr-icon fr-icon--xs fr-icon-question-line"
                    aria-describedby="params-{model.id}"
                  ></a>
                {/if}
              </span>
              {#if model.release_date}
                <span class="fr-badge fr-badge--no-icon fr-mr-1v">
                  {m['models.release']({ date: model.release_date })}
                </span>
              {/if}

              <span class="fr-badge fr-badge--no-icon fr-mr-1v">
                {#if model.distribution === 'open-weights'}
                  {m['models.licenses.name']({ licence: model.license })}
                {:else}
                  {m['models.licenses.commercial']()}
                {/if}
              </span>
            </p>
            <p>{model.description}</p>
            <div>
              <h6 class="fr-mb-0">{m['models.size.title']()}</h6>
              <p class="fr-mb-4w text-grey fr-text--sm">
                {#if model.distribution === 'open-weights'}
                  {m[`models.openWeight.descriptions.${model.friendly_size}`]({
                    paramsCount: Math.round(model.params)
                  })}
                {/if}
                {m[`models.size.descriptions.${model.friendly_size}`]()}
              </p>
            </div>
            <div class="fr-mb-4w">
              <h6 class="fr-mb-0">{m['models.conditions']()}</h6>
              <div class="fr-mb-1w">
                {#if model.distribution === 'open-weights'}
                  <p class="fr-text--sm text-grey">
                    <!-- FIXME i18n integrate licenseDesc in translations -->
                    <strong>{m['models.licenses.name']({ licence: model.license })}</strong>&nbsp;:
                    {infos.licenseDesc[model.license] || m['models.licenses.noDesc']()}
                  </p>
                  <div class="model-details grid">
                    <div class="rounded-tile fr-px-1v fr-py-1w relative">
                      <!-- FIXME i18n -->
                      {#if infos.licenseAttrs?.[model.license]?.warning_commercial}
                        <Icon icon="checkbox-circle-fill" block class="text-warning" />
                      {:else if infos.licenseAttrs?.[model.license]?.prohibit_commercial}
                        <Icon icon="close-circle-fill" block class="text-error" />
                      {:else}
                        <Icon icon="checkbox-circle-fill" block class="text-success" />
                      {/if}
                      <span class="text-grey-200 fr-text--xs fr-mb-0"
                        >{m['models.openWeight.use.commercial']()}</span
                      >
                    </div>
                    <div class="rounded-tile fr-px-1v fr-py-1w relative">
                      <Icon icon="checkbox-circle-fill" block class="text-success" />
                      <span class="text-grey-200 fr-text--xs fr-mb-0"
                        >{m['models.openWeight.use.modification']()}</span
                      >
                    </div>
                    <div class="rounded-tile fr-px-1v fr-py-1w relative">
                      <Icon icon="checkbox-circle-fill" block class="text-success" />
                      <span class="text-grey-200 fr-text--xs fr-mb-0"
                        >{m['models.openWeight.use.attribution']()}</span
                      >
                    </div>
                    <div class="rounded-tile fr-px-1v fr-py-1w relative">
                      <a
                        class="fr-icon fr-icon--xs fr-icon-question-line"
                        aria-describedby="license-type-{model.id}"
                      ></a>
                      <span class="fr-badge fr-badge--sm">
                        {m[`models.openWeight.conditions.${model.conditions}`]()}
                      </span>
                      <span class="text-grey-200 fr-text--xs fr-mb-0"
                        >{m['models.openWeight.use.licenseType']()}</span
                      >
                    </div>
                    <div class="rounded-tile fr-px-1v fr-py-1w relative">
                      <a
                        class="fr-icon fr-icon--xs fr-icon-question-line"
                        aria-describedby="ram-{model.id}"
                      ></a>
                      <span class="fr-badge fr-badge--sm">
                        {m['models.ram']({
                          min: model.required_ram / 2,
                          max: model.required_ram * 2
                        })}
                      </span>
                      <span class="text-grey-200 fr-text--xs fr-mb-0"
                        >{m['models.openWeight.use.requiredRam']()}</span
                      >
                    </div>
                  </div>
                {:else}
                  <p class="fr-text--sm text-grey">
                    {infos.licenseDesc[model.license] || m['models.licenses.noDesc']()}
                  </p>
                {/if}
              </div>
            </div>

            <h6>Pour aller plus loin</h6>
            <p class="text-grey">
              {@html sanitize(
                m[`models.extra.experts.${model.distribution}`]({
                  linkProps: externalLinkProps(model.url || '#')
                })
              )}
              <br />
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
    </div>
  </div>

  {#if model.distribution === 'open-weights'}
    <span class="fr-tooltip fr-placement" id="license-{model.id}" role="tooltip" aria-hidden="true">
      {#if model.fully_open_source}
        {m['models.openWeight.tooltips.openSource']()}
      {:else}
        {m['models.openWeight.tooltips.openWeight']()}
      {/if}
    </span>

    <span class="fr-tooltip fr-placement" id="params-{model.id}" role="tooltip" aria-hidden="true">
      {m['models.openWeight.tooltips.params']()}
    </span>
    <span
      class="fr-tooltip fr-placement"
      id="license-type-{model.id}"
      role="tooltip"
      aria-hidden="true"
    >
      {#if model.conditions === 'copyleft' || model.conditions === 'free'}
        {m[`models.openWeight.tooltips.${model.conditions}`]()}
      {/if}
    </span>
    <span class="fr-tooltip fr-placement" id="ram-{model.id}" role="tooltip" aria-hidden="true">
      {m['models.openWeight.tooltips.ram']()}
    </span>
  {/if}
</dialog>
