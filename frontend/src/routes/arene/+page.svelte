<script lang="ts">
  import { Icon, Link, Tooltip } from '$components/dsfr'
  import Header from '$components/header/Header.svelte'
  import SeoHead from '$components/SEOHead.svelte'
  import { arena, modeInfos } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { TOSModal, ViewChat, ViewPrompt } from './components'

  const mode = $derived(arena.mode ? modeInfos.find((mode) => mode.value === arena.mode)! : null)
  let toggled = $state(false)

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

{#snippet desc()}
  <p class="mt-2! mb-0! text-sm! leading-normal! text-grey md:mt-0!">
    {#if arena.chat.step == 1}
      {m['header.chatbot.stepOne.description']()}
    {:else}
      {m['header.chatbot.stepTwo.description']()}
    {/if}
  </p>
{/snippet}

{#snippet extra()}
  {#if arena.chat.step == 1}
    <div
      class="cg-border rounded-lg! mt-2 bg-white py-1 text-sm md:mt-0 md:py-3 w-full border-dashed! text-center"
    >
      <Icon icon={mode!.icon} size="sm" class="text-primary" />
      &nbsp;<strong>{mode!.title}</strong>
      &nbsp;<Tooltip id="mode-desc" text={mode!.description} size="xs" />
    </div>
  {:else}
    <div class="md:block hidden text-right">
      <!-- TODO missing share page, hide btn for now -->
      <!-- <Button
        icon="upload-2-line"
        variant="secondary"
        text={m['reveal.feedback.shareResult']()}
        data-fr-opened="false"
        aria-controls="share-modal"
      /> -->
      <!--<a class="btn purple-btn" href="../arene/?cgu_acceptees" target="_blank"><svg width="21" height="20" viewBox="0 0 21 20" fill="none"
      xmlns="http://www.w3.org/2000/svg">
  </svg>&nbsp;Reposer ma question</a>-->
      <Link
        button
        icon="edit-line"
        href="../arene/?cgu_acceptees"
        text={m['header.chatbot.newDiscussion']()}
        class="md:w-auto! w-full!"
      />
    </div>
  {/if}
{/snippet}

{#if arena.currentScreen === 'chat' && arena.chat.step && mode}
  <div
    bind:this={secondHeader}
    id="second-header"
    class="fr-container--fluid bg-light-grey top-0 py-3 md:py-4 sticky z-3 drop-shadow-[--raised-shadow]"
  >
    <div class="fr-container gap-3 md:flex-row flex flex-col items-center">
      <div class="gap-3 md:flex-row flex basis-2/3 flex-col items-center">
        <div class="bg-primary px-4 py-2 font-bold text-white rounded-[3.75rem] text-nowrap">
          {m['header.chatbot.step']()}
          {arena.chat.step}/2
        </div>
        <div class="md:text-left flex flex-col text-center">
          <strong class="text-dark-grey">
            {#if arena.chat.step == 1}
              {m['header.chatbot.stepOne.title']()}
            {:else}
              {m['header.chatbot.stepTwo.title']()}
            {/if}
          </strong>
          {#if arena.chat.step == 1}
            <div class="fr-accordion md:hidden before:shadow-none!">
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
                <Icon
                  icon={toggled ? 'i-ri-arrow-up-s-line' : 'i-ri-arrow-down-s-line'}
                  size="sm"
                  block
                />
                <span class="sr-only">{m['actions.seeMore']()}</span>
              </button>
            </div>
          {:else}
            <div class="md:hidden">{@render desc()}</div>
          {/if}
          <div class="md:block hidden">{@render desc()}</div>
        </div>
      </div>
      <div class="md:block hidden w-full basis-1/3 items-center">
        {@render extra()}
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
