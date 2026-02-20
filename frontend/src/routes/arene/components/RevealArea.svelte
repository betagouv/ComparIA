<script lang="ts">
  import AILogo from '$components/AILogo.svelte'
  import { Badge, Button, Link, Tooltip } from '$components/dsfr'
  import ModelInfoModal from '$components/ModelInfoModal.svelte'
  import type { RevealData } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'
  import { MiniCard } from '.'

  let { data }: { data: RevealData } = $props()

  const locale = getLocale()

  const { selected, modelsData, shareB64Data, equivalences } = data

  let shareInput: HTMLInputElement

  function copyShareLink() {
    shareInput.select()
    navigator.clipboard.writeText(shareInput.value)
    useToast(m['actions.copyLink.done'](), 2000)
  }
</script>

<div id="reveal-area" class="fr-container mt-8! md:mt-10!" {@attach scrollTo}>
  <div class="gap-5 lg:grid-cols-2 lg:gap-6 grid">
    {#each modelsData as { model, pos, scaled_co2_t, energy_mwh, tokens } (pos)}
      {@const modelBadges = (['license', 'size', 'releaseDate'] as const)
        .map((k) => model.badges[k])
        .filter((b) => !!b)}

      <div class="cg-border bg-white p-5 md:p-7 md:pb-10 flex flex-col">
        <div>
          <h5 class="fr-h6 mb-4! text-dark-grey! gap-2 flex items-center">
            <AILogo iconPath={model.icon_path} size="lg" alt={model.organisation} />
            <div><span class="font-normal">{model.organisation}/</span>{model.simple_name}</div>
            {#if selected === pos}
              <div
                class="border-primary text-primary px-3 font-bold ms-auto rounded-[3.75rem] border bg-[--blue-france-975-75] text-[14px]"
              >
                {m['vote.yours']()}
              </div>
            {/if}
          </h5>
          <ul class="fr-badges-group mb-4!">
            {#each modelBadges as badge, i (i)}
              <li><Badge id="card-badge-{i}" {...badge} noTooltip /></li>
            {/each}
          </ul>

          {@html sanitize(model.desc).replaceAll('<p>', '<p class="fr-text--sm text-grey!">')}
        </div>

        <h6 class="mb-5! text-base! mt-auto!">
          {m['reveal.impacts.title']()}
          <Tooltip id="impact-{pos}" text={m['reveal.impacts.tooltip']()} />
        </h6>
        <div class="flex">
          <div class="md:basis-2/3 md:flex-row flex basis-1/2 flex-col">
            <div class="md:w-full relative">
              <MiniCard
                id="params-{pos}"
                value={model.params}
                desc={m['reveal.impacts.size.label']()}
                tooltip={m['models.openWeight.tooltips.params']()}
                class="-mb-2 bg-white z-1 h-full "
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
                class="cg-border rounded-sm! p-1 ps-3 pt-2 leading-normal absolute z-0 flex w-full bg-[--beige-gris-galet-950-100] text-[11px]"
              >
                <span class="text-[--beige-gris-galet-sun-407-moon-821]">
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

            <strong class="mb-1 md:mx-1 md:my-auto m-auto text-[20px]">×</strong>

            <MiniCard
              id="tokens-{pos}"
              value={tokens}
              units={m['reveal.impacts.tokens.tokens']()}
              desc={m['reveal.impacts.tokens.label']()}
              tooltip={m['reveal.impacts.tokens.tooltip']()}
              class="md:w-full"
            />
          </div>

          <div class="md:basis-1/3 flex basis-1/2 items-center">
            <strong class="m-auto">≈</strong>

            <MiniCard
              id="energy-{pos}"
              value={energy_mwh.toFixed(energy_mwh < 2 ? 2 : 0)}
              units="mWh"
              desc={m['reveal.impacts.energy.label']()}
              icon="i-ri-flashlight-fill"
              iconClass="text-info"
              tooltip={m['reveal.impacts.energy.tooltip']()}
              class="h-fit"
            />
          </div>
        </div>

        <div class="mt-9! md:mt-14! mb-5!">
          <div class="flex">
            <div>
              <h6 class="text-base! mb-0!">
                {m['reveal.equivalent.title']()}
                <Tooltip id="equivalent-{pos}">
                  {@html sanitize(
                    m['reveal.equivalent.title_tooltip']({
                      linkProps: externalLinkProps({
                        href: 'https://www.credoc.fr/publications/barometre-du-numerique-2026-rapport'
                      })
                    })
                  )}
                </Tooltip>
              </h6>
              <p>{m['reveal.equivalent.desc']()}</p>
            </div>

            <!-- FIXME -->
            <MiniCard
              id="co2-{pos}"
              value={scaled_co2_t < 1
                ? scaled_co2_t.toFixed(3)
                : scaled_co2_t < 10
                  ? scaled_co2_t.toFixed(1)
                  : scaled_co2_t.toFixed(0)}
              units="tonnes"
              desc={m['reveal.equivalent.co2.label']()}
              tooltip={m['reveal.equivalent.co2.tooltip']()}
              class="md:w-full"
            />
          </div>

          {#each equivalences as eq, i (i)}
            <div>
              <strong>{eq[pos].toFixed(1)}</strong>
              <p>
                {m[`reveal.equivalent.scales.${eq.type}.unit`]()}
                <Tooltip id="equivalent-{eq.type}-{pos}">
                  {@html sanitize(
                    m[`reveal.equivalent.scales.${eq.type}.tooltip`]({
                      linkProps: externalLinkProps({
                        href: 'FIXME'
                      })
                    })
                  )}
                </Tooltip>
              </p>
            </div>
          {/each}
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
    <div class="fr-container md:max-w-[280px]! gap-4 flex flex-col items-center">
      <Link
        button
        icon="edit-line"
        href="../arene/?cgu_acceptees"
        text={m['header.chatbot.newDiscussion']()}
        class="md:hidden! w-full!"
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

                <p class="mb-0! text-sm!">
                  {m['reveal.feedback.description']()}
                </p>
                <div class="gap-3 py-8 flex flex-wrap">
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

{#if ['fr', 'en'].includes(locale)}
  <section class="fr-container--fluid bg-light-info">
    <div class="fr-container">
      <div class="gap-x-15 lg:gap-x-30 lg:px-15 gap-y-10 py-8 md:flex-row flex flex-col">
        <div class="flex max-w-[350px] flex-col">
          <h5 class="font mb-3!">{m['reveal.thanks.title']()}</h5>
          <p class="mb-8!">{m['reveal.thanks.desc']()}</p>

          <Link
            button
            size="lg"
            href="/ranking"
            icon="trophy-line"
            text={m['reveal.thanks.cta']()}
            class="sm:w-auto! w-full!"
          />
        </div>

        <div class="relative flex max-w-[640px] items-start">
          <img
            src="/images/ranking-table.png"
            class="rounded-xl shadow-md md:-me-[10%] -me-[30%] w-full max-w-[400px]"
            alt={m['reveal.thanks.rankingAlt']()}
          />
          <img
            src="/images/ranking-graph.png"
            class="rounded-xl shadow-md mt-[30px] w-full max-w-[300px]"
            alt={m['reveal.thanks.graphAlt']()}
          />
        </div>
      </div>
    </div>
  </section>
{/if}

<style>
  #reveal-area {
    scroll-margin-top: calc(var(--second-header-size) + 1rem);
  }
</style>
