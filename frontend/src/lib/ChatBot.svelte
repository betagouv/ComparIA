<script lang="ts">
  import type { OnReactionFn, RevealData, VoteData } from '$lib/chatService.svelte'
  import {
    askChatBots,
    chatbot,
    getReveal,
    postVoteGetReveal,
    retryAskChatBots,
    updateReaction
  } from '$lib/chatService.svelte'
  import ChatBot from '$lib/components/ChatBot.svelte'
  import RevealArea from '$lib/components/RevealArea.svelte'
  import TextPrompt from '$lib/components/TextPrompt.svelte'
  import VoteArea from '$lib/components/VoteArea.svelte'
  import { m } from '$lib/i18n/messages'

  let rtl = false
  let layout: 'bubble' | 'panel' = 'bubble'
  let latex_delimiters: {
    left: string
    right: string
    display: boolean
  }[] = []
  let placeholder: string | null = null

  let step = $state<'chat' | 'vote' | 'reveal'>('chat')
  let prompt = $state('')
  let canVote = $state<boolean | null>(true)
  let voteData = $state<VoteData>({
    selected: undefined,
    a: {
      like: [],
      dislike: [],
      comment: ''
    },
    b: {
      like: [],
      dislike: [],
      comment: ''
    }
  })
  let revealData = $state<RevealData>()

  const chatbotDisabled = $derived(chatbot.status !== 'complete' || step !== 'chat')
  const revealDisabled = $derived(
    chatbot.status !== 'complete' || (step === 'vote' && voteData.selected === undefined)
  )

  const onReactionChange: OnReactionFn = async (kind, reaction) => {
    canVote = false
    await updateReaction(kind, reaction)
  }

  function onRetry() {
    retryAskChatBots()
  }

  async function onPromptSubmit() {
    await askChatBots(prompt)
  }

  async function onRevealModels() {
    // if chat as reactions, no need to show vote
    if (canVote === false) {
      revealData = await getReveal()
      step = 'reveal'
    } else if (step === 'vote') {
      if (!voteData.selected) return
      revealData = await postVoteGetReveal(voteData as Required<VoteData>)
      step = 'reveal'
    } else {
      step = 'vote'
    }
  }

  // Compute second header height for autoscrolling
  let footer = $state<HTMLElement>()
  let footerSize: number = $state(0)

  function onResize() {
    footerSize = footer ? footer.offsetHeight : 0
  }

  $effect(() => {
    footerSize = footer ? footer.offsetHeight : 0
  })
</script>

<svelte:window onresize={onResize} />

<div id="chat-area" style="--footer-size: {footerSize}px;">
  <ChatBot
    disabled={chatbotDisabled}
    pending={chatbot.status === 'pending'}
    generating={chatbot.status === 'generating'}
    {onReactionChange}
    {onRetry}
    {layout}
  />
</div>

{#if step === 'vote' || step === 'reveal'}
  <VoteArea bind:value={voteData} disabled={step === 'reveal'} />
{/if}

{#if step === 'reveal' && revealData}
  <RevealArea data={revealData} />
{:else}
  <div
    bind:this={footer}
    id="send-area"
    class="mt-auto flex flex-col items-center gap-3 px-4 py-3 md:px-[20%]"
  >
    {#if step === 'chat'}
      <div class="flex w-full flex-col gap-3 md:flex-row">
        <TextPrompt
          id="chatbot-prompt"
          bind:value={prompt}
          label={m['chatbot.continuePrompt']()}
          placeholder={m['chatbot.continuePrompt']()}
          hideLabel
          rows={2}
          maxRows={4}
          autofocus
          onSubmit={onPromptSubmit}
          class="mb-0! w-full"
        />

        <button
          id="send-btn"
          disabled={chatbot.status !== 'complete' || prompt === ''}
          class="btn purple-btn md:self-end"
          onclick={onPromptSubmit}
        >
          {m['words.send']()}
        </button>
      </div>
    {/if}

    <button
      disabled={revealDisabled}
      class="btn purple-btn w-full md:w-fit"
      onclick={onRevealModels}
    >
      {m['chatbot.revealButton']()}
    </button>
  </div>
{/if}

<style>
  #send-area {
    position: sticky;
    width: 100%;
    bottom: 0;
    left: 0;
    background-color: var(--main-background);
    z-index: 100;
  }
</style>
