<script lang="ts">
  import Icon from '$lib/components/Icon.svelte'
  import Toaster from '$lib/components/Toaster.svelte'
  import Tooltip from '$lib/components/Tooltip.svelte'
  import { m } from '$lib/i18n/messages'
  import { setLocale } from '$lib/i18n/runtime'
  import { modeInfos, infos } from '$lib/state.svelte'
  import { sanitize } from '$lib/utils/commons'
  import '../css/app.css'
  // import MobileMenu from '$lib/components/MobileMenu.svelte'
  import Menubar from '$lib/components/Menubar.svelte'

  let { children } = $props()
  const mode = $derived(infos.mode ? modeInfos.find((mode) => mode.value === infos.mode)! : null)
  // FIXME i18n
  const NumberFormater = new Intl.NumberFormat('fr', { maximumSignificantDigits: 3 })
  const votes = $derived(
    infos.votes
      ? {
          count: NumberFormater.format(infos.votes.count),
          objective: NumberFormater.format(infos.votes.objective),
          ratio: (100 * (infos.votes.count / infos.votes.objective)).toFixed() + '%'
        }
      : null
  )

  // Compute second header height for autoscrolling
  let secondHeader = $state<HTMLElement>()
  let secondHeaderSize: number = $state(0)

  function onResize() {
    secondHeaderSize = secondHeader ? secondHeader.offsetHeight : 0
  }

  $effect(() => {
    secondHeaderSize = secondHeader ? secondHeader.offsetHeight : 0
  })
</script>

<svelte:window onresize={onResize} />

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

        {#if infos.currentScreen === 'initial'}
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
                {m['header.chatbot.vote.total']()}&nbsp;<Tooltip
                  id="gauge"
                  size="xs"
                  label={m['header.chatbot.vote.legend']()}
                >
                  {@html sanitize(m['header.chatbot.vote.tooltip']())}
                </Tooltip>
              </span>
              <div class="linear-gauge" style:--gauge-ratio={votes?.ratio}>
                <div class="linear-gauge-fill">
                  <span class="votes">{votes?.count}</span>
                </div>
              </div>
              <span class="objectif">{m['header.chatbot.vote.objective']()}{votes?.objective}</span>
            </div>
          </div>
        {/if}

        <div class="translate">
          <button onclick={() => setLocale('en')}>EN</button>
          <button onclick={() => setLocale('fr')}>FR</button>
        </div>
      </div>
    </div>
  </div>
  <Menubar></Menubar>
  <!-- <MobileMenu></MobileMenu> -->
  <!-- <Bunka></Bunka> -->
</header>

{#if infos.currentScreen === 'chatbots' && infos.step && mode}
  <div
    bind:this={secondHeader}
    id="second-header"
    class="fr-container--fluid fr-py-1w sticky top-0"
  >
    <div class="fr-mb-0 fr-container fr-grid-row">
      <div class="fr-col-12 fr-col-md-8 align-center column md-row flex">
        <div>
          <span class="step-badge fr-mt-md-0 fr-mb-md-0 fr-mt-1w fr-mb-3v">
            {m['header.chatbot.step']()}
            {infos.step}/2
          </span>
        </div>
        <p class="fr-ml-1w fr-mb-md-0 fr-mb-md-1v md-text-left mb-0! text-center">
          <strong class="text-dark-grey">
            {#if infos.step == 1}
              {m['header.chatbot.stepOne.title']()}
            {:else}
              {m['header.chatbot.stepTwo.title']()}
            {/if}
          </strong>
          <br />
          <span class="text-grey fr-text--xs">
            {#if infos.step == 1}
              {m['header.chatbot.stepOne.description']()}
            {:else}
              {m['header.chatbot.stepTwo.description']()}
            {/if}
          </span>
        </p>
      </div>
      <div class="fr-col-12 fr-col-md-4 align-center grid">
        {#if infos.step == 1}
          <div class="mode-sticker fr-pt-1w fr-pb-1v fr-text--xs mb-0! bg-white text-center">
            <Icon icon={mode.icon} size="sm" class="text-primary" />
            &nbsp;<strong>{mode.title}</strong>
            &nbsp;<Tooltip id="mode-desc" text={mode.description} size="xs" />
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
{/if}

<main class="relative" style="--second-header-size: {secondHeaderSize}px;">
  <Toaster />

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
