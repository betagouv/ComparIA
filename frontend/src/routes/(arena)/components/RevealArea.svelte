<script lang="ts">
  import { Button, Link } from '$components/dsfr'
  import SideSwitcher from '$components/SideSwitcher.svelte'
  import { parseAPIRevealData, type APIRevealData } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import type { UsageProfileId } from '$lib/usageProfiles'
  import { RevealCard } from '.'

  let { data }: { data: APIRevealData } = $props()

  const { selected, modelsData, shareB64Data } = $derived(parseAPIRevealData(data))
  let usageProfile = $state<UsageProfileId>('discussion')
  let impactTab = $state<'explanation' | 'equivalences'>('explanation')
  let modelTitleHeights = $state<Record<string, number>>({})
  const modelTitleHeight = $derived(Math.max(0, ...Object.values(modelTitleHeights)))

  let shareInput: HTMLInputElement

  function copyShareLink() {
    shareInput.select()
    navigator.clipboard.writeText(shareInput.value)
    useToast(m['actions.copyLink.done'](), 2000)
  }

  function updateModelTitleHeight(pos: string, height: number) {
    if (modelTitleHeights[pos] === height) return

    modelTitleHeights = { ...modelTitleHeights, [pos]: height }
  }
</script>

<div id="reveal-area" class="fr-container--fluid mt-8! md:mt-10!" {@attach scrollTo}>
  <div class="px-4 md:px-6">
    <SideSwitcher>
      <div class="gap-4 sm:gap-6 md:w-full flex">
        {#each modelsData as data, index (data.pos)}
          <div class="md:w-full min-w-0 w-[85vw]">
            <RevealCard
              {data}
              otherData={modelsData[index === 0 ? 1 : 0]}
              selected={selected === data.pos}
              {usageProfile}
              onUsageProfileChange={(profile) => (usageProfile = profile)}
              {impactTab}
              onImpactTabChange={(tab) => (impactTab = tab)}
              {modelTitleHeight}
              onModelTitleHeightChange={(height) => updateModelTitleHeight(data.pos, height)}
            />
          </div>
        {/each}
      </div>
    </SideSwitcher>

    <div class="feedback py-7 border-b-1 border-[#CECECE]">
      <div class="fr-container md:max-w-[280px]! gap-4 flex flex-col items-center">
        <Link
          button
          icon="edit-line"
          href="/"
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
                  <h2 id="fr-modal-title-share-modal" class="fr-h6 mb-3! text-dark-grey!">
                    {m['reveal.feedback.shareResult']()}
                  </h2>

                  <p class="mb-0! text-sm!">
                    {m['reveal.feedback.description']()}
                  </p>
                  <div class="gap-3 py-8 flex flex-wrap">
                    <label class="sr-only" for="share-link">{m['a11y.shareLinkLabel']()}</label>
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
</div>

<style>
  #reveal-area {
    scroll-margin-top: calc(var(--second-header-size) + 1rem);
    background: linear-gradient(
      180deg,
      var(--cg-very-light-grey) 0%,
      var(--blue-france-950-100) 50%,
      var(--brand-primary-soft) 100%
    );
  }
</style>
