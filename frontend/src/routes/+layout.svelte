<script lang="ts">
  import IconModel from '$lib/components/IconModel.svelte'
  import { m } from '$lib/i18n/messages'
  import { setLocale } from '$lib/i18n/runtime'
  import { modeInfos, state } from '$lib/state.svelte'
  import { sanitize } from '$lib/utils/commons'
  import '../css/app.css'

  let { children } = $props()
  const mode = $derived(state.mode ? modeInfos.find((mode) => mode.value === state.mode)! : null)
  // FIXME i18n
  const NumberFormater = new Intl.NumberFormat('fr', { maximumSignificantDigits: 3 })
  const votes = $derived(
    state.votes
      ? {
          count: NumberFormater.format(state.votes.count),
          objective: NumberFormater.format(state.votes.objective),
          ratio: (100 * (state.votes.count / state.votes.objective)).toFixed() + '%'
        }
      : null
  )
</script>

<header id="main-header" class="fr-header">
  <div class="fr-header__body">
    <div class="fr-container">
      <div class="fr-header__body-row fr-grid-row">
        <div class="fr-header__brand fr-enlarge-link">
          <div class="fr-col-4">
            <div class="fr-header__logo">
              <p class="fr-logo">
                République<br />Française
              </p>
            </div>
          </div>
          <div class="fr-col-6 fr-col-lg-12">
            <a href="/" title="Accueil - compar:IA" target="_blank">
              <p class="fr-header__service-title">
                {m['header.title.compar']()}:{m['header.title.ia']()}
              </p>
            </a>

            <span class="fr-header__service-tagline">
              {m['header.subtitle']()}
            </span>
          </div>
          <!-- <div class="fr-header__navbar fr-col-2">
            <button class="fr-btn fr-btn--menu" data-fr-opened="false" aria-controls="fr-modal-menu" aria-haspopup="menu"
              title="Menu"> Menu</button>
          </div> -->
        </div>

        {#if state.currentScreen === 'initial'}
          <div class="md-visible fr-header__tools fr-col-12 fr-col-lg-4 fr-p-2w hidden">
            <a
              title={m['header.help.link.title']()}
              href="https://adtk8x51mbw.eu.typeform.com/to/duuGRyEX"
              target="_blank"
              rel="noopener external"
              class="fr-link fr-icon-pencil-line fr-link--icon-left"
            >
              {m['header.help.link.content']()}
            </a>
          </div>
        {:else}
          <div class=" fr-header__tools fr-col-12 fr-col-lg-6 fr-p-md-2w md-visible hidden">
            <div class="fr-container--fluid counter">
              <span class="fr-ml-1w legende">
                {m['header.chatbot.vote.total']()}&nbsp;<a
                  aria-describedby="gauge"
                  href="#gauge"
                  aria-label={m['header.chatbot.vote.legend']()}
                  class="fr-icon fr-icon--xs fr-icon--question-line"
                ></a>
              </span>
              <div class="linear-gauge" style:--gauge-ratio={votes?.ratio}>
                <div class="linear-gauge-fill">
                  <span class="votes">{votes?.count}</span>
                </div>
              </div>
              <span class="objectif">{m['header.chatbot.vote.objective']()}{votes?.objective}</span>
            </div>
            <span class="fr-tooltip fr-placement" id="gauge" role="tooltip" aria-hidden="true">
              {@html sanitize(m['header.chatbot.vote.tooltip']())}
            </span>
          </div>
        {/if}

        <div class="translate">
          <button onclick={() => setLocale('en')}>EN</button>
          <button onclick={() => setLocale('fr')}>FR</button>
        </div>
      </div>
    </div>
  </div>
</header>

{#if state.currentScreen === 'chatbots' && state.step && mode}
  <div id="second-header" class="fr-container--fluid fr-py-1w">
    <div class="fr-mb-0 fr-container fr-grid-row">
      <div class="fr-col-12 fr-col-md-8 align-center column md-row flex">
        <div>
          <span class="step-badge fr-mt-md-0 fr-mb-md-0 fr-mt-1w fr-mb-3v">
            {m['header.chatbot.step']()}
            {state.step}/2
          </span>
        </div>
        <p class="fr-ml-1w fr-mb-md-0 fr-mb-md-1v md-text-left text-center">
          <strong class="text-dark-grey">
            {#if state.step == 1}
              {m['header.chatbot.stepOne.title']()}
            {:else}
              {m['header.chatbot.stepTwo.title']()}
            {/if}
          </strong>
          <br />
          <span class="text-grey fr-text--xs">
            {#if state.step == 1}
              {m['header.chatbot.stepOne.description']()}
            {:else}
              {m['header.chatbot.stepTwo.description']()}
            {/if}
          </span>
        </p>
      </div>
      <div class="fr-col-12 fr-col-md-4 align-center grid">
        {#if state.step == 1}
          <div class="mode-sticker fr-pt-1w fr-pb-1v fr-text--xs bg-white text-center">
            <IconModel icon={mode.icon} size={20} inline />
            &nbsp;<strong>{mode.title}</strong>
            &nbsp;<a class="fr-icon fr-icon--xs fr-icon--question-line" aria-describedby="mode-desc"
            ></a>
          </div>
        {:else}
          <div class="text-center">
            <!--<a class="btn purple-btn" href="../arene/?cgu_acceptees" target="_blank"><svg width="21" height="20" viewBox="0 0 21 20" fill="none"
                xmlns="http://www.w3.org/2000/svg">
            </svg>&nbsp;Reposer ma question</a>-->
            <a
              class="btn purple-btn md-visible hidden"
              href="../arene/?cgu_acceptees"
              target="_blank"
            >
              {m['header.chatbot.newDiscussion']()}
            </a>
          </div>
        {/if}
      </div>
    </div>
  </div>

  <span class="fr-tooltip fr-placement" id="mode-desc" role="tooltip" aria-hidden="true">
    {mode.description}
  </span>
{/if}

<main>
  {@render children()}
</main>

<style>
  #main-header {
    z-index: 800;
    --shadow-color: rgba(0, 0, 18, 0.16);
    --raised-shadow: 0 1px 3px var(--shadow-color);
    filter: drop-shadow(0 1px 3px var(--shadow-color));
  }

  .legende {
    font-size: 0.875em;
    color: #161616 !important;
    font-weight: bold;
  }

  .votes {
    font-size: 0.75em;
    font-weight: bold;
    color: #695240 !important;
    margin-left: 5px;
    height: inherit;
    float: left;
  }

  .objectif {
    font-weight: 500;
    font-size: 0.75em;
    color: #7f7f7f !important;
  }

  .linear-gauge-fill {
    width: 0%; /* Start at 0% for the animation */
    height: 100%;
    border-radius: 4px;
    background-color: #fde39c !important;
    /* Add the transition property */
    transition: width 1s ease-out 0.5s; /* 1s duration, ease-out timing, 0.5s delay */
  }

  /* This keyframe animation sets the final width after the delay */
  @keyframes fillGauge {
    to {
      width: var(--gauge-ratio);
    }
  }

  /* Apply the animation to the linear-gauge-fill */
  .linear-gauge-fill {
    animation: fillGauge 1s ease-out 0.5s forwards; /* Same duration, timing, and delay */
  }

  .linear-gauge {
    width: 200px;
    height: 20px;
    background: #fff;
    border-radius: 4px;
    border: 1px solid #cccccc;
    overflow: hidden;
  }

  .counter {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1em;
    padding-top: 0;
    padding-bottom: 1em;
    height: auto;
  }

  .objectif {
    display: block;
  }

  #second-header {
    width: 100%;
    z-index: 750;
    background-color: #f3f5f9;
    --shadow-color: rgba(0, 0, 18, 0.16);
    --raised-shadow: 0 1px 3px var(--shadow-color);
    filter: drop-shadow(0 1px 3px var(--shadow-color));
  }

  .text-dark-grey {
    color: #3a3a3a;
  }

  .mode-sticker {
    z-index: 750;
    border-radius: 0.5em;
    border: #e5e5e5 dashed 1px;
  }

  .align-center {
    align-items: center;
  }

  .column {
    flex-direction: column;
  }

  @media (min-width: 48em) {
    .md-row {
      flex-direction: row;
    }

    .md-text-left {
      text-align: left !important;
    }
  }

  main {
    background-color: var(--main-background);
  }
</style>
