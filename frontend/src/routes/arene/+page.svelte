<script lang="ts">
  import { Icon, Link, Tooltip } from '$components/dsfr'
  import Header from '$components/header/Header.svelte'
  import SeoHead from '$components/SEOHead.svelte'
  import { arena, modeInfos, runChatBots } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { ViewChat, ViewPrompt, WelcomeModal } from './components'

  const mode = $derived(arena.mode ? modeInfos.find((mode) => mode.value === arena.mode)! : null)
  let toggled = $state(false)

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

<SeoHead title={m['seo.titles.arene']()} />

<WelcomeModal />

<Header
  hideNavigation
  hideDiscussBtn
  hideVoteGauge={arena.currentScreen === 'prompt'}
  hideLanguageSelector={arena.currentScreen === 'chat'}
  showHelpLink={arena.currentScreen === 'prompt'}
  small
/>

{#snippet desc()}
  <p class="text-grey text-sm! mb-0! leading-normal! mt-2! md:mt-0!">
    {#if arena.chat.step == 2}
      {m['header.chatbot.stepOne.description']()}
    {:else}
      {m['header.chatbot.stepTwo.description']()}
    {/if}
  </p>
{/snippet}

{#snippet extra()}
  {#if arena.chat.step == 1}
    <div
      class="cg-border border-dashed! rounded-lg! mt-2 w-full bg-white py-1 text-center text-sm md:mt-0 md:py-3"
    >
      <Icon icon={mode!.icon} size="sm" class="text-primary" />
      &nbsp;<strong>{mode!.title}</strong>
      &nbsp;<Tooltip id="mode-desc" text={mode!.description} size="xs" />
    </div>
  {:else}
    <div class="hidden text-right md:block">
      <!--<a class="btn purple-btn" href="../arene/?cgu_acceptees" target="_blank"><svg width="21" height="20" viewBox="0 0 21 20" fill="none"
      xmlns="http://www.w3.org/2000/svg">
  </svg>&nbsp;Reposer ma question</a>-->
      <Link
        button
        href="../arene/?cgu_acceptees"
        text={m['header.chatbot.newDiscussion']()}
        class="w-full! md:w-auto!"
      />
    </div>
  {/if}
{/snippet}

{#if arena.currentScreen === 'chat' && arena.chat.step && mode}
  <div
    bind:this={secondHeader}
    id="second-header"
    class="fr-container--fluid bg-light-grey drop-shadow-(--raised-shadow) z-2 sticky top-0 py-3 md:py-4"
  >
    <div class="fr-container flex flex-col items-center gap-3 md:flex-row">
      <div class="flex basis-2/3 flex-col items-center gap-3 md:flex-row">
        <div class="bg-primary text-nowrap rounded-[3.75rem] px-4 py-2 font-bold text-white">
          {m['header.chatbot.step']()}
          {arena.chat.step}/2
        </div>
        <div class="flex flex-col text-center md:text-left">
          <strong class="text-dark-grey">
            {#if arena.chat.step == 1}
              {m['header.chatbot.stepOne.title']()}
            {:else}
              {m['header.chatbot.stepTwo.title']()}
            {/if}
          </strong>
          {#if arena.chat.step == 1}
            <div class="fr-accordion before:shadow-none! md:hidden">
              <div id="accordion-header" class="fr-collapse p-0!">
                {@render desc()}
                {@render extra()}
              </div>
              <button
                type="button"
                class=""
                aria-expanded="false"
                aria-controls="accordion-header"
                onclick={() => (toggled = !toggled)}
              >
                <Icon icon={toggled ? 'arrow-up-s-line' : 'arrow-down-s-line'} size="sm" block />
                <span class="sr-only">{m['actions.seeMore']()}</span>
              </button>
            </div>
          {:else}
            <div class="md:hidden">{@render desc()}</div>
          {/if}
          <div class="hidden md:block">{@render desc()}</div>
        </div>
      </div>
      <div class="hidden w-full basis-1/3 items-center md:block">
        {@render extra()}
      </div>
    </div>
  </div>
{/if}

<main class="bg-very-light-grey relative" style="--second-header-size: {secondHeaderSize}px;">
  {#if arena.currentScreen === 'prompt'}
    <ViewPrompt onSubmit={runChatBots} />
  {:else}
    <ViewChat />
  {/if}
</main>
