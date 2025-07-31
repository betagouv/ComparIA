<script lang="ts">
  import ChatBot from '$lib/ChatBot.svelte'
  import { arena, modeInfos, runChatBots } from '$lib/chatService.svelte'
  import Header from '$lib/components/header/Header.svelte'
  import Icon from '$lib/components/Icon.svelte'
  import Tooltip from '$lib/components/Tooltip.svelte'
  import DropDown from '$lib/DropDown.svelte'
  import { m } from '$lib/i18n/messages'
  import WelcomeModal from './WelcomeModal.svelte'

  let { data } = $props()

  const mode = $derived(arena.mode ? modeInfos.find((mode) => mode.value === arena.mode)! : null)

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

<WelcomeModal />

<Header
  hideNavigation
  hideVoteGauge={arena.currentScreen === 'prompt'}
  hideLanguageSelector={arena.currentScreen === 'chat'}
  showHelpLink={arena.currentScreen === 'prompt'}
/>

{#if arena.currentScreen === 'chat' && arena.chat.step && mode}
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
            {arena.chat.step}/2
          </span>
        </div>
        <p class="fr-ml-1w fr-mb-md-0 fr-mb-md-1v md-text-left mb-0! text-center">
          <strong class="text-dark-grey">
            {#if arena.chat.step == 1}
              {m['header.chatbot.stepOne.title']()}
            {:else}
              {m['header.chatbot.stepTwo.title']()}
            {/if}
          </strong>
          <br />
          <span class="text-grey fr-text--xs">
            {#if arena.chat.step == 1}
              {m['header.chatbot.stepOne.description']()}
            {:else}
              {m['header.chatbot.stepTwo.description']()}
            {/if}
          </span>
        </p>
      </div>
      <div class="fr-col-12 fr-col-md-4 align-center grid">
        {#if arena.chat.step == 1}
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
  {#if arena.currentScreen === 'prompt'}
    <DropDown onSubmit={runChatBots} models={data.models} />
  {:else}
    <ChatBot />
  {/if}
</main>

<style>
  main {
    background-color: var(--main-background);
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
</style>
