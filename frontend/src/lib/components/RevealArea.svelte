<script lang="ts">
  import type { RevealData } from '$lib/chatService.svelte'
  import Footer from '$lib/components/Footer.svelte'
  import ModelInfoModal from '$lib/components/ModelInfoModal.svelte'
  import { m } from '$lib/i18n/messages'
  import { externalLinkProps, sanitize } from '$lib/utils/commons'

  let { data }: { data: RevealData } = $props()

  const { selected, modelsData, shareB64Data, ...infos } = data

  let shareInput: HTMLInputElement
  // FIXME refactor into component
  let snackbar: HTMLElement

  function copyShareLink() {
    shareInput.select()
    navigator.clipboard.writeText(shareInput.value)
    createSnackbar('Lien copié dans le presse-papiers')
  }

  function createSnackbar(message: string) {
    const messageText = snackbar.querySelector('.message')
    messageText!.textContent = message

    snackbar.classList.add('show')

    setTimeout(() => {
      snackbar.classList.remove('show')
    }, 2000)
  }

  function closeSnackbar() {
    snackbar.classList.remove('show')
  }
</script>

<div id="reveal-screen" class="fr-pt-4w next-screen">
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
              <span
                class="fr-tooltip fr-placement"
                id="params-{side}"
                role="tooltip"
                aria-hidden="true"
              >
                {m['models.openWeight.tooltips.params']()}
              </span>
              <p>
                <a
                  class="fr-icon fr-icon--xs fr-icon-question-line"
                  aria-describedby="params-{side}"
                ></a>
              </p>

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
              <span
                class="fr-tooltip fr-placement"
                id="tokens-{side}"
                role="tooltip"
                aria-hidden="true"
              >
                {m['reveal.impacts.tokens.tooltip']()}
              </span>
              <p>
                <a
                  class="fr-icon fr-icon--xs fr-icon-question-line"
                  aria-describedby="tokens-{side}"
                ></a>
              </p>
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
              <span
                class="fr-tooltip fr-placement"
                id="energie-{side}"
                role="tooltip"
                aria-hidden="true"
              >
                {m['reveal.impacts.energy.tooltip']()}
              </span>
              <a class="fr-icon fr-icon--xs fr-icon-question-line" aria-describedby="energie-{side}"
              ></a>
              <div class="">
                <!-- flashlight -->
                <svg
                  transform="scale(1.33)"
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  width="24"
                  height="24"
                  class=""
                >
                  <path fill="#0063cb" d="M13 10h7l-9 13v-9H4l9-13v9Z" />
                </svg>
              </div>
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
              <span
                class="fr-tooltip fr-placement"
                id="co2-{side}"
                role="tooltip"
                aria-hidden="true"
              >
                {@html sanitize(m['reveal.equivalent.co2.tooltip']())}
              </span>

              <a class="fr-icon fr-icon--xs fr-icon-question-line" aria-describedby="co2-{side}"
              ></a>
              <div class="">
                <!-- cloud -->
                <svg
                  transform="scale(1.33)"
                  class=""
                  width="21"
                  height="17"
                  viewBox="0 0 21 17"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fill-rule="evenodd"
                    clip-rule="evenodd"
                    d="M15.4556 16.5001H6.36473C3.70538 16.5016 1.43245 14.7449 0.984647 12.342C0.536847 9.93905 2.04472 7.59035 4.55382 6.78255C4.44169 4.63438 5.62808 2.60391 7.64094 1.49905C9.6538 0.394196 12.1666 0.394196 14.1794 1.49905C16.1923 2.60391 17.3787 4.63438 17.2666 6.78255C19.7757 7.59035 21.2835 9.93905 20.8357 12.342C20.3879 14.7449 18.115 16.5016 15.4556 16.5001Z"
                    fill="#CFCFCF"
                  />
                </svg>
              </div>
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
              <span
                class="fr-tooltip fr-placement"
                id="ampoule-{side}"
                role="tooltip"
                aria-hidden="true"
              >
                {m['reveal.equivalent.lightbulb.tooltip']()}
              </span>
              <a class="fr-icon fr-icon--xs fr-icon-question-line" aria-describedby="ampoule-{side}"
              ></a>
              <div class="">
                <!-- lightbulb -->
                <svg
                  transform="scale(1.33)"
                  class=""
                  width="14"
                  height="19"
                  viewBox="0 0 14 19"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fill-rule="evenodd"
                    clip-rule="evenodd"
                    d="M6.16953 14H3.62036C3.37286 12.9391 2.2562 12.0716 1.79786 11.5C-0.384161 8.77374 -0.0927751 4.82569 2.46585 2.44933C5.02447 0.0729714 8.98325 0.0736052 11.5411 2.45078C14.099 4.82796 14.3891 8.7761 12.2062 11.5016C11.7479 12.0725 10.6329 12.94 10.3854 14H7.83619V9.83331H6.16953V14ZM10.3362 15.6666V16.5C10.3362 17.4205 9.59 18.1666 8.66953 18.1666H5.33619C4.41572 18.1666 3.66953 17.4205 3.66953 16.5V15.6666H10.3362Z"
                    fill="#EFCB3A"
                  />
                </svg>
              </div>
              <div class="">
                <p>
                  <strong><span class="fr-text--xxl">{lightbulb}</span>{lightbulbUnit}</strong>
                </p>
                <p class="fr-text--xs">{m['reveal.equivalent.lightbulb.label']()}</p>
              </div>
            </div>
            <div class="rounded-tile with-icon fr-px-1w fr-py-1w relative">
              <a class="fr-icon fr-icon--xs fr-icon-question-line" aria-describedby="videos-{side}"
              ></a>
              <span
                class="fr-tooltip fr-placement"
                id="videos-{side}"
                role="tooltip"
                aria-hidden="true"
              >
                {@html sanitize(
                  m['reveal.equivalent.streaming.tooltip']({
                    linkProps: externalLinkProps(
                      'https://impactco2.fr/outils/usagenumerique/streamingvideo'
                    )
                  })
                )}
              </span>
              <div class="">
                <!-- youtube -->
                <svg
                  transform="scale(1.33)"
                  width="20"
                  height="20"
                  viewBox="0 0 20 20"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M1.66406 3.32783C1.66406 2.87063 2.04349 2.5 2.49056 2.5H17.5042C17.9607 2.5 18.3307 2.87079 18.3307 3.32783V16.6722C18.3307 17.1293 17.9513 17.5 17.5042 17.5H2.49056C2.0341 17.5 1.66406 17.1292 1.66406 16.6722V3.32783ZM8.84898 7.01216C8.79423 6.97565 8.72989 6.95617 8.66406 6.95617C8.47998 6.95617 8.33073 7.10541 8.33073 7.28951V12.7105C8.33073 12.7763 8.35023 12.8407 8.38673 12.8954C8.48881 13.0486 8.69581 13.09 8.84898 12.9878L12.9147 10.2773C12.9513 10.2529 12.9827 10.2215 13.0071 10.1849C13.1093 10.0317 13.0679 9.82475 12.9147 9.72267L8.84898 7.01216Z"
                    fill="#F95A5C"
                  />
                </svg>
              </div>
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
      <div class="fr-container fr-mb-4w text-center">
        <a class="btn fr-btn--secondary fr-my-2w feedback-btns" href="/" target="_blank">
          {m['actions.returnHome']()}
        </a><br />
        <button
          class="btn fr-btn--secondary fr-my-2w feedback-btns"
          data-fr-opened="false"
          aria-controls="share-modal"
        >
          <svg
            class="inline"
            width="21"
            height="20"
            viewBox="0 0 21 20"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M10.5 2.15479L15.6726 7.32737L14.4941 8.50585L11.3333 5.34513V13.3333H9.66667V5.34513L6.50592 8.50585L5.32741 7.32737L10.5 2.15479ZM3 14.9999V11.6666H4.66667V14.9999C4.66667 15.4602 5.03977 15.8333 5.5 15.8333H15.5C15.9602 15.8333 16.3333 15.4602 16.3333 14.9999V11.6666H18V14.9999C18 16.3807 16.8807 17.4999 15.5 17.4999H5.5C4.11929 17.4999 3 16.3807 3 14.9999Z"
              fill="#6A6AF4"
            />
          </svg>&nbsp;{m['reveal.feedback.shareResult']()}
        </button><br />
        <!-- Remplacer par https://monitor.bunka.ai/compar:ia ? -->
        <a
          class="fr-mx-auto fr-mb-4w link"
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
                  <button class="fr-col-md-4 fr-col-12 btn purple-btn block" onclick={copyShareLink}
                    ><svg
                      width="15"
                      height="16"
                      viewBox="0 0 15 16"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      class="inline"
                    >
                      <path
                        d="M8.29571 5.08317L9.35636 6.14383C11.4066 8.19412 11.4066 11.5182 9.35636 13.5685L9.09124 13.8336C7.04096 15.8839 3.71685 15.8839 1.6666 13.8336C-0.383657 11.7834 -0.383657 8.45924 1.6666 6.409L2.72726 7.46969C1.2628 8.93414 1.2628 11.3085 2.72726 12.7729C4.19173 14.2374 6.56606 14.2374 8.03059 12.7729L8.29571 12.5078C9.76016 11.0433 9.76016 8.66894 8.29571 7.20449L7.23506 6.14383L8.29571 5.08317ZM13.3338 9.59099L12.2732 8.53034C13.7376 7.06582 13.7376 4.69148 12.2732 3.22702C10.8087 1.76255 8.43439 1.76255 6.96994 3.22702L6.70474 3.49218C5.24027 4.95664 5.24027 7.33102 6.70474 8.79547L7.76539 9.85612L6.70474 10.9168L5.64407 9.85612C3.59382 7.80592 3.59382 4.48177 5.64407 2.43152L5.90924 2.16635C7.95949 0.116099 11.2836 0.116099 13.3338 2.16635C15.3841 4.2166 15.3841 7.54072 13.3338 9.59099Z"
                        fill="white"
                      />
                    </svg>&nbsp;{m['actions.copyLink']()}</button
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

    <div id="snackbar" bind:this={snackbar}>
      <div class="checkmark">
        <svg
          width="16"
          height="15"
          viewBox="0 0 16 15"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            fill-rule="evenodd"
            clip-rule="evenodd"
            d="M8.25477 13.7224C4.91029 13.7224 2.19922 11.0114 2.19922 7.66688C2.19922 4.3224 4.91029 1.61133 8.25477 1.61133C11.5993 1.61133 14.3103 4.3224 14.3103 7.66688C14.3103 11.0114 11.5993 13.7224 8.25477 13.7224ZM7.65104 10.0891L11.9323 5.80722L11.0761 4.95097L7.65104 8.3766L5.93792 6.66348L5.08166 7.51973L7.65104 10.0891Z"
            fill="white"
          />
        </svg>
      </div>
      <span class="message"></span><span class="close" onclick={closeSnackbar()}
        ><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="12" height="12">
          <path
            d="m12 10.6 4.95-4.96 1.4 1.4L13.42 12l4.96 4.95-1.4 1.4L12 13.42l-4.95 4.96-1.4-1.4L10.58 12 5.63 7.05l1.4-1.4z"
          />
        </svg></span
      >
    </div>
  </div>
</div>

<Footer />

<style>
  #snackbar {
    position: fixed;
    bottom: 20px;
    right: 20px;
    border: 2px solid #6a6af4;
    background-color: white;
    color: #333;
    box-shadow: 0 1px 5px rgba(0, 0, 0, 0.1);
    display: flex;
    align-items: stretch;
    /* just enough! */
    z-index: 1750;
    visibility: hidden;
    opacity: 0;
    transition:
      opacity 0.3s ease-in-out,
      visibility 0s linear 0.3s;
  }

  :global(#snackbar.show) {
    visibility: visible;
    opacity: 1;
    transition: opacity 0.3s ease-in-out;
  }

  #snackbar .checkmark {
    display: flex;
    height: 100%;
    align-items: center;
    justify-content: center;
    padding: 10px;
    background-color: #6a6af4;
  }

  #snackbar .message {
    align-items: center;
    display: flex;
    padding: 0 20px;
  }

  #snackbar .close {
    margin-right: 10px;
    align-items: center;
    justify-content: center;
    display: flex;
    cursor: pointer;
    color: #333;
  }
</style>
