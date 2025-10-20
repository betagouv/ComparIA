<script lang="ts">
  import { Badge, Button, Link, Tooltip } from '$components/dsfr'
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
      {@const modelBadges = (['license', 'size', 'releaseDate'] as const)
        .map((k) => model.badges[k])
        .filter((b) => !!b)}
      {@const wh = kwh * 1000}

      <div class="cg-border flex flex-col bg-white p-5 md:p-7 md:pb-10">
        <div>
          <h5 class="fr-h6 text-dark-grey! mb-4! flex items-center gap-2">
            <img src="/orgs/ai/{model.icon_path}" width="34" aria-hidden="true" alt="" />
            <div><span class="font-normal">{model.organisation}/</span>{model.simple_name}</div>
            {#if selected === side}
              <div
                class="bg-(--blue-france-975-75) text-primary border-primary ms-auto rounded-[3.75rem] border px-3 text-[14px] font-bold"
              >
                {m['vote.yours']()}
              </div>
            {/if}
          </h5>
          <ul class="fr-badges-group mb-4!">
            {#each modelBadges as badge, i}
              <li><Badge id="card-badge-{i}" {...badge} noTooltip /></li>
            {/each}
          </ul>

          {@html sanitize(model.desc).replaceAll('<p>', '<p class="fr-text--sm text-grey!">')}
        </div>

        <h6 class="mt-auto! mb-5! text-base!">{m['reveal.impacts.title']()}</h6>
        <div class="flex">
          <div class="flex basis-1/2 flex-col md:basis-2/3 md:flex-row">
            <div class="relative md:w-full">
              <MiniCard
                id="params-{side}"
                value={model.params}
                desc={m['reveal.impacts.size.label']()}
                tooltip={m['models.openWeight.tooltips.params']()}
                class="z-10 -mb-2 h-full bg-white "
              >
                {m['reveal.impacts.size.count']()}
                {#if model.distribution === 'api-only'}
                  {m['reveal.impacts.size.estimated']()}
                {/if}
                {#if model.quantization === 'q8'}
                  {m['reveal.impacts.size.quantized']()}
                {/if}
              </MiniCard>
              <div
                class="cg-border rounded-sm! bg-(--beige-gris-galet-950-100) absolute z-0 flex w-full p-1 ps-3 pt-2 text-[11px] leading-normal"
              >
                <span class="text-(--beige-gris-galet-sun-407-moon-821)">
                  {model.badges.arch.text}
                </span>
                <Tooltip
                  id="{model.id}-arch-tooltip"
                  size="xs"
                  text={model.badges.arch.tooltip}
                  class="ms-auto"
                />
              </div>
            </div>

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
              value={wh.toFixed(wh < 2 ? 2 : 0)}
              units="Wh"
              desc={m['reveal.impacts.energy.label']()}
              icon="flashlight-fill"
              iconClass="text-info"
              tooltip={m['reveal.impacts.energy.tooltip']()}
              class="h-fit"
            />
          </div>
        </div>

        <h6 class="mt-9! md:mt-14! mb-5! text-base!">{m['reveal.equivalent.title']()}</h6>
        <div class="grid grid-cols-3 gap-2">
          <MiniCard
            id="co2-{side}"
            value={co2.toFixed(co2 < 2 ? 2 : 0)}
            units="g"
            desc={m['reveal.equivalent.co2.label']()}
            icon="cloudy-2-fill"
            iconClass="text-(--grey-975-75-active)"
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
            size="sm"
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
        icon="edit-line"
        href="../arene/?cgu_acceptees"
        text={m['header.chatbot.newDiscussion']()}
        class="w-full! md:hidden!"
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
    </div>

    <dialog aria-labelledby="fr-modal-title-share-modal" id="share-modal" class="fr-modal">
      <div class="fr-container fr-container--fluid fr-container-md">
        <div class="fr-grid-row fr-grid-row--center">
          <div class="fr-col-12 fr-col-md-8 fr-col-lg-6">
            <div class="fr-modal__body rounded-xl">
              <div class="fr-modal__header">
                <Button
                  variant="tertiary-no-outline"
                  text={m['words.close']()}
                  title={m['closeModal']()}
                  aria-controls="share-modal"
                  class="fr-btn--close"
                />
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
                    value="https://comparia.beta.gouv.fr/share?i={shareB64Data}"
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
