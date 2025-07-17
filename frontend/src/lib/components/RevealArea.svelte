<script lang="ts">
  import type { RevealData } from '$lib/chatService.svelte'
  import Footer from '$lib/components/Footer.svelte'
  import Icon from '$lib/components/Icon.svelte'
  import ModelInfoModal from '$lib/components/ModelInfoModal.svelte'
  import Tooltip from '$lib/components/Tooltip.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'
  import { onMount } from 'svelte'

  let { data }: { data: RevealData } = $props()

  const { selected, modelsData, shareB64Data, ...infos } = data

  let elem: HTMLDivElement
  let shareInput: HTMLInputElement

  function copyShareLink() {
    shareInput.select()
    navigator.clipboard.writeText(shareInput.value)
    useToast(m['actions.copyLink.done'](), 2000)
  }

  onMount(() => {
    elem.scrollIntoView({ behavior: 'smooth' })
  })
</script>

<div bind:this={elem} id="reveal-screen" class="fr-pt-4w next-screen">
  <div>
    <div id="reveal-grid" class="grid-cols-md-2 fr-mx-md-12w grid grid-cols-1">
      {#each modelsData as { model, side, kwh, co2, tokens, lightbulb, lightbulbUnit, streaming, streamingUnit } (side)}
        <div class="rounded-tile fr-mb-1w fr-p-4w fr-mx-3v bg-white text-left">
          {#if selected === side}
            <span class="your-choice fr-mb-2w fr-mb-md-0">{m['vote.yours']()}</span>
          {/if}
          <h5 class="fr-mb-2w github-title">
            <img class="fr-mt-n2v relative inline" src="/orgs/{model.icon_path}" width="34" />
            {model.organisation}/<strong>{model.simple_name}</strong>
          </h5>
          <p class="fr-mb-2w">
            {#if model.fully_open_source}
              <span class="fr-badge fr-badge--green-emeraude fr-badge--no-icon fr-mr-1v fr-mb-1v">
                {m['models.licenses.type.openSource']()}&nbsp;
              </span>
            {:else if model.distribution === 'open-weights'}
              <span class="fr-badge fr-badge--yellow-tournesol fr-badge--no-icon fr-mr-1v fr-mb-1v">
                {m['models.licenses.type.semiOpen']()}&nbsp;
              </span>
            {:else}
              <span
                class="fr-badge fr-badge--orange-terre-battue fr-badge--no-icon fr-mr-1v fr-mb-1v"
              >
                {m['models.licenses.type.proprietary']()}
              </span>
            {/if}
            <span class="fr-badge fr-badge--no-icon fr-badge--info fr-mr-1v fr-mb-1v">
              {#if model.distribution === 'api-only'}
                {m['models.size.estimated']({ size: model.friendly_size })}
              {:else}
                {m['models.parameters']({ number: model.params })}
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
          <p class="fr-mb-4w fr-text--sm text-grey-200">{model.excerpt}</p>
          <h6 class="fr-mb-2w">{m['reveal.impacts.title']()}</h6>
          <div class="energy-balance-1">
            <div class="rounded-tile fr-px-1w fr-py-1w relative text-center">
              <Tooltip
                id="params-{side}"
                text={m['models.openWeight.tooltips.params']()}
                size="xs"
              />

              <div class="">
                <p class="">
                  <strong>
                    <span class="fr-text--xxl">{model.params}</span>
                    <span class="fr-text--xs">
                      {m['reveal.impacts.size.count']()}
                      {#if model.distribution !== 'open-weights'}
                        {m['reveal.impacts.size.estimated']()}
                      {/if}
                      {#if model.quantization === 'q8'}
                        {m['reveal.impacts.size.quantized']()}
                      {/if}
                    </span>
                  </strong>
                </p>
                <p class="fr-text--sm">{m['reveal.impacts.size.label']()}</p>
              </div>
            </div>
            <div class="self-center justify-self-center">
              <strong>×</strong>
            </div>
            <div class="rounded-tile fr-px-1w fr-py-1w relative text-center">
              <Tooltip id="tokens-{side}" text={m['reveal.impacts.tokens.tooltip']()} size="xs" />
              <div class="">
                <p class="">
                  <strong>
                    <span class="fr-text--xxl">{tokens}</span>
                    <span class="fr-text--xs">{m['reveal.impacts.tokens.tokens']()}</span>
                  </strong>
                </p>
                <p class="fr-text--sm">{m['reveal.impacts.tokens.label']()}</p>
              </div>
            </div>

            <div class="self-center justify-self-center">
              <strong>=</strong>
            </div>
            <div class="rounded-tile with-icon fr-px-1w fr-py-1w relative">
              <Tooltip id="energie-{side}" text={m['reveal.impacts.energy.tooltip']()} size="xs" />
              <Icon icon="flashlight-fill" size="lg" block class="text-info" />
              <div class="">
                <!-- FIXME co2?? should be kwh? -->
                <p>
                  <strong>
                    <span class="fr-text--xxl">{co2.toFixed(co2 < 2 ? 2 : 0)}</span> Wh
                  </strong>
                </p>
                <p class="fr-text--xs">{m['reveal.impacts.energy.label']()}</p>
              </div>
            </div>
          </div>
          <h6 class="fr-mt-4w fr-mb-2w">Ce qui correspond à :</h6>
          <div class="energy-balance-2">
            <div class="rounded-tile with-icon fr-px-1w fr-py-1w relative">
              <Tooltip id="co2-{side}" size="xs">
                {@html sanitize(m['reveal.equivalent.co2.tooltip']())}
              </Tooltip>
              <Icon icon="cloudy-2-fill" size="lg" block class="text-grey" />
              <div class="">
                <p>
                  <strong>
                    <span class="fr-text--xxl">{co2.toFixed(co2 < 2 ? 2 : 0)}</span> g
                  </strong>
                </p>
                <p class="fr-text--xs">{@html sanitize(m['reveal.equivalent.co2.label']())}</p>
              </div>
            </div>
            <div class="rounded-tile with-icon fr-px-1w fr-py-1w relative">
              <Tooltip
                id="ampoule-{side}"
                text={m['reveal.equivalent.lightbulb.tooltip']()}
                size="xs"
              />
              <Icon icon="lightbulb-fill" size="lg" block class="text-yellow" />
              <div class="">
                <p>
                  <strong><span class="fr-text--xxl">{lightbulb}</span>{lightbulbUnit}</strong>
                </p>
                <p class="fr-text--xs">{m['reveal.equivalent.lightbulb.label']()}</p>
              </div>
            </div>
            <div class="rounded-tile with-icon fr-px-1w fr-py-1w relative">
              <Tooltip id="videos-{side}" size="xs">
                {@html sanitize(
                  m['reveal.equivalent.streaming.tooltip']({
                    linkProps: externalLinkProps(
                      'https://impactco2.fr/outils/usagenumerique/streamingvideo'
                    )
                  })
                )}
              </Tooltip>
              <Icon icon="youtube-fill" size="lg" block class="text-error" />
              <div class="">
                <p>
                  <strong><span class="fr-text--xxl">{streaming}</span>{streamingUnit}</strong>
                </p>
                <p class="fr-text--xs">{m['reveal.equivalent.streaming.label']()}</p>
              </div>
            </div>
          </div>
          <div class="fr-grid-row fr-grid-row--center fr-mt-4w">
            <button
              class="fr-btn--sm grey-btn"
              data-fr-opened="false"
              aria-controls="fr-modal-{model.id}"
            >
              {m['actions.seeMore']()}
            </button>
          </div>
        </div>

        <ModelInfoModal {model} {infos} />
      {/each}
    </div>
  </div>

  <div class="feedback">
    <div id="feedback-row">
      <div class="fr-container fr-mb-4w flex flex-col items-center text-center">
        <a class="btn fr-btn--secondary fr-my-2w feedback-btns" href="/" target="_blank">
          {m['actions.returnHome']()}
        </a><br />
        <button
          class="btn fr-icon-upload-2-line fr-btn--icon-left fr-btn--secondary fr-my-2w feedback-btns"
          data-fr-opened="false"
          aria-controls="share-modal"
        >
          {m['reveal.feedback.shareResult']()}
        </button>
        <!-- Remplacer par https://monitor.bunka.ai/compar:ia ? -->
        <a
          class="fr-mb-4w link"
          href="https://languia-metabase.stg.cloud.culture.fr/public/dashboard/7dde3be2-6680-49ac-966b-ade9ad36dfcf?tab=29-tableau-1"
          target="_blank">{m['reveal.feedback.moreOnVotes']()}</a
        >
      </div>
    </div>

    <dialog
      aria-labelledby="fr-modal-title-share-modal"
      role="dialog"
      id="share-modal"
      class="fr-modal"
    >
      <div class="fr-container fr-container--fluid fr-container-md">
        <div class="fr-grid-row fr-grid-row--center">
          <div class="fr-col-12 fr-col-md-8 fr-col-lg-6">
            <div class="fr-modal__body">
              <div class="fr-modal__header">
                <button
                  class="fr-btn--close fr-btn"
                  title={m['closeModal']()}
                  aria-controls="share-modal">{m['words.close']()}</button
                >
              </div>
              <div class="fr-modal__content">
                <h6 class="fr-text--lg">{m['reveal.feedback.shareResult']()}</h6>
                <p class="fr-text-md--sm fr-text--xs">
                  {m['reveal.feedback.description']()}
                </p>
                <div class="fr-grid-row fr-mb-4w">
                  <input
                    bind:this={shareInput}
                    type="text"
                    id="share-link"
                    class="fr-col-md-8 fr-col-12 fr-input inline"
                    value="https://www.comparia.beta.gouv.fr/share?i={shareB64Data}"
                  />
                  <button
                    class="fr-col-md-4 fr-icon-links-fill fr-btn--icon-left fr-col-12 btn purple-btn block"
                    onclick={copyShareLink}
                  >
                    {m['actions.copyLink.do']()}</button
                  >
                </div>
                <img
                  class="fr-responsive-img fr-mb-4w"
                  src="../assets/share-example.png"
                  alt={m['reveal.feedback.example']()}
                  title={m['reveal.feedback.example']()}
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </dialog>
  </div>
</div>

<Footer />

<style>
  #reveal-screen {
    scroll-margin-top: calc(var(--second-header-size) + 1rem);
    min-height: 70vh;
  }
</style>
