<script lang="ts">
  import { Button, Link } from '$components/dsfr'
  import { parseAPIRevealData, type APIRevealData } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { RevealCard } from '.'

  let { data }: { data: APIRevealData } = $props()

  const locale = getLocale()

  const { selected, modelsData, shareB64Data } = $derived(parseAPIRevealData(data))

  let shareInput: HTMLInputElement

  function copyShareLink() {
    shareInput.select()
    navigator.clipboard.writeText(shareInput.value)
    useToast(m['actions.copyLink.done'](), 2000)
  }
</script>

<div id="reveal-area" class="fr-container mt-8! md:mt-10!" {@attach scrollTo}>
  <div class="gap-5 lg:grid-cols-2 lg:gap-6 grid grid-cols-1">
    {#each modelsData as data (data.pos)}
      <RevealCard {data} selected={selected === data.pos} />
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
