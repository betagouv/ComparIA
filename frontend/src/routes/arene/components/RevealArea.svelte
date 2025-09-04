<script lang="ts">
  import { Badge, Button, Link } from '$components/dsfr'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import type { RevealData } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'
  import { MiniCard } from '.'

  let { data }: { data: RevealData } = $props()

  const { selected, modelsData, shareB64Data } = data

  let shareInput: HTMLInputElement

  function copyShareLink() {
    shareInput.select()
    navigator.clipboard.writeText(shareInput.value)
    useToast(m['actions.copyLink.done'](), 2000)
  }
</script>

<div id="reveal-area" class="fr-container mt-8! md:mt-10!" {@attach scrollTo}>
  <div class="grid gap-5 lg:grid-cols-2 lg:gap-6">
    {#each modelsData as { model, side, kwh, co2, tokens, lightbulb, lightbulbUnit, streaming, streamingUnit } (side)}
      {@const modelBadges = (['license', 'size', 'releaseDate', 'licenseName'] as const)
        .map((k) => model.badges[k])
        .filter((b) => !!b)}

      <div class="cg-border flex flex-col bg-white p-5 md:p-7 md:pb-10">
        <div>
          {#if selected === side}
            <div
              class="bg-primary mb-3 inline-block text-nowrap rounded-[3.75rem] px-4 py-2 font-bold text-white"
            >
              {m['vote.yours']()}
            </div>
          {/if}
          <h5 class="text-dark-grey! mb-4! flex items-center gap-2">
            <img src="/orgs/ai/{model.icon_path}" width="34" aria-hidden="true" alt="" />
            <div><span class="font-normal">{model.organisation}/</span>{model.simple_name}</div>
          </h5>
          <ul class="fr-badges-group mb-4!">
            {#each modelBadges as badge, i}
              <li><Badge id="card-badge-{i}" {...badge} noTooltip /></li>
            {/each}
          </ul>

          {@html sanitize(model.desc).replaceAll('<p>', '<p class="fr-text--sm text-grey!">')}
        </div>

        <h6 class="mt-auto! mb-5!">{m['reveal.impacts.title']()}</h6>
        <div class="flex">
          <div class="flex basis-1/2 flex-col md:basis-2/3 md:flex-row">
            <MiniCard
              id="params-{side}"
              value={model.params}
              desc={m['reveal.impacts.size.label']()}
              tooltip={m['models.openWeight.tooltips.params']()}
              class="md:w-full"
            >
              {m['reveal.impacts.size.count']()}
              {#if model.distribution !== 'open-weights'}
                {m['reveal.impacts.size.estimated']()}
              {/if}
              {#if model.quantization === 'q8'}
                {m['reveal.impacts.size.quantized']()}
              {/if}
            </MiniCard>

            <strong class="m-auto mb-1 text-[20px] md:mx-1 md:my-auto">×</strong>

            <MiniCard
              id="tokens-{side}"
              value={tokens}
              units={m['reveal.impacts.tokens.tokens']()}
              desc={m['reveal.impacts.tokens.label']()}
              tooltip={m['reveal.impacts.tokens.tooltip']()}
              class="md:w-full"
            />
          </div>

          <div class="flex basis-1/2 items-center md:basis-1/3">
            <strong class="m-auto">=</strong>

            <MiniCard
              id="energy-{side}"
              value={kwh.toFixed(kwh < 2 ? 2 : 0)}
              units="Wh"
              desc={m['reveal.impacts.energy.label']()}
              icon="flashlight-fill"
              iconClass="text-info"
              tooltip={m['reveal.impacts.energy.tooltip']()}
              class="h-fit"
            />
          </div>
        </div>

        <h6 class="mt-9! mb-5!">{m['reveal.equivalent.title']()}</h6>
        <div class="grid grid-cols-3 gap-2">
          <MiniCard
            id="co2-{side}"
            value={co2.toFixed(co2 < 2 ? 2 : 0)}
            units="g"
            desc={m['reveal.equivalent.co2.label']()}
            icon="cloudy-2-fill"
            iconClass="text-grey"
            tooltip={m['reveal.equivalent.co2.tooltip']()}
          />

          <MiniCard
            id="ampoule-{side}"
            value={lightbulb}
            units={lightbulbUnit}
            desc={m['reveal.equivalent.lightbulb.label']()}
            icon="lightbulb-fill"
            iconClass="text-yellow"
            tooltip={m['reveal.equivalent.lightbulb.tooltip']()}
          />

          <MiniCard
            id="videos-{side}"
            value={streaming}
            units={streamingUnit}
            desc={m['reveal.equivalent.streaming.label']()}
            icon="youtube-fill"
            iconClass="text-error"
            tooltip={m['reveal.equivalent.streaming.tooltip']({
              linkProps: externalLinkProps(
                'https://impactco2.fr/outils/usagenumerique/streamingvideo'
              )
            })}
          />
        </div>

        <div class="mt-7 text-center">
          <Button
            text={m['actions.seeMore']()}
            data-fr-opened="false"
            aria-controls="modal-model-reveal-{model.id}"
          />
        </div>
      </div>

      <ModelInfoModal {model} modalId="modal-model-reveal-{model.id}" />
    {/each}
  </div>

  <div class="feedback py-7">
    <div class="fr-container md:max-w-[280px]! flex flex-col items-center gap-4">
      <Link
        button
        href="../arene/?cgu_acceptees"
        text={m['header.chatbot.newDiscussion']()}
        class="w-full!"
      />

      <!-- TODO missing share page, hide btn for now -->
      <!-- <Button
        icon="upload-2-line"
        variant="secondary"
        text={m['reveal.feedback.shareResult']()}
        data-fr-opened="false"
        aria-controls="share-modal"
        class="w-full!"
      /> -->

      <!-- Remplacer par https://monitor.bunka.ai/compar:ia ? -->
      <Link
        native={false}
        href="https://metabase.comparia.beta.gouv.fr/public/dashboard/7dde3be2-6680-49ac-966b-ade9ad36dfcf?tab=29-tableau-1"
        target="_blank"
        text={m['reveal.feedback.moreOnVotes']()}
      />
    </div>

    <dialog
      aria-labelledby="fr-modal-title-share-modal"
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
                  aria-controls="share-modal"
                >
                  {m['words.close']()}
                </button>
              </div>
              <div class="fr-modal__content">
                <h6 class="mb-3! text-dark-grey!">
                  {m['reveal.feedback.shareResult']()}
                </h6>

                <p class="text-sm! mb-0!">
                  {m['reveal.feedback.description']()}
                </p>
                <div class="flex flex-wrap gap-3 py-8">
                  <input
                    bind:this={shareInput}
                    type="text"
                    id="share-link"
                    class="fr-col-md-8 fr-col-12 fr-input inline"
                    value="https://www.comparia.beta.gouv.fr/share?i={shareB64Data}"
                  />
                  <Button
                    icon="links-fill"
                    onclick={copyShareLink}
                    text={m['actions.copyLink.do']()}
                  />
                </div>
                <img
                  class="fr-responsive-img"
                  src="/share-example.png"
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

<style>
  #reveal-area {
    scroll-margin-top: calc(var(--second-header-size) + 1rem);
  }
</style>
