<script lang="ts">
  import { Link } from '$components/dsfr'
  import Header from '$components/header/Header.svelte'
  import SeoHead from '$components/SEOHead.svelte'
  import { fetchAndSolve } from '$lib/captcha.svelte'
  import { arena, modeInfos } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { TOSModal, ViewChat, ViewPrompt } from './components'

  // Start solving Altcha challenge on page load (runs in background)
  fetchAndSolve()

  const mode = $derived(arena.mode ? modeInfos.find((mode) => mode.value === arena.mode)! : null)

  // Compute second header height for autoscrolling
  let secondHeader = $state<HTMLElement>()
  let secondHeaderSize = $derived<number>(secondHeader?.offsetHeight ?? 0)

  function onResize() {
    secondHeaderSize = secondHeader ? secondHeader.offsetHeight : 0
  }
</script>

<svelte:window onresize={onResize} />

<SeoHead title={m['seo.titles.arene']()} />

<TOSModal />

<Header
  hideNavigation
  hideDiscussBtn
  hideVoteGauge={arena.currentScreen === 'prompt'}
  hideLanguageSelector={arena.currentScreen === 'chat'}
  showHelpLink={arena.currentScreen === 'prompt'}
  small
/>

{#if arena.currentScreen === 'chat' && arena.chat.step === 'reveal' && mode}
  <div
    bind:this={secondHeader}
    id="second-header"
    class="fr-container--fluid bg-light-grey top-0 py-3 md:py-4 sticky z-3 drop-shadow-[--raised-shadow]"
  >
    <div class="fr-container gap-3 md:flex-row flex flex-col items-center">
      <div class="gap-3 md:flex-row flex basis-2/3 flex-col items-center">
        <div class="bg-primary px-4 py-2 font-bold text-white rounded-[3.75rem] text-nowrap">
          {m['header.chatbot.reveal.title']()}
        </div>
        <div class="md:text-left flex flex-col text-center">
          <strong class="text-dark-grey">
            {m['header.chatbot.reveal.subtitle']()}
          </strong>
          <p class="mt-2! mb-0! text-sm! leading-normal! text-grey md:mt-0!">
            {m['header.chatbot.reveal.description']()}
          </p>
        </div>
      </div>
      <div class="md:block hidden w-full basis-1/3 items-center text-right">
        <Link
          button
          icon="edit-line"
          href="../arene/?cgu_acceptees"
          text={m['header.chatbot.newDiscussion']()}
          class="md:w-auto! w-full!"
        />
      </div>
    </div>
  </div>
{/if}

<main class="bg-very-light-grey relative" style="--second-header-size: {secondHeaderSize}px;">
  {#if arena.currentScreen === 'prompt'}
    <ViewPrompt />
  {:else}
    <ViewChat />
  {/if}
</main>
