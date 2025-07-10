<script lang="ts">
  import { chatbot } from '$lib/chatService.svelte'
  import ChatBot from '$lib/components/ChatBot.svelte'
  import TextPrompt from '$lib/components/TextPrompt.svelte'
  import VoteArea, { type VoteData } from '$lib/components/VoteArea.svelte'
  import { m } from '$lib/i18n/messages'
  import type { ExtendedLikeData } from '$lib/types'
  import type { UndoRetryData } from '$lib/utils'

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

  const chatbotDisabled = $derived(chatbot.status !== 'complete' || step !== 'chat')
  const revealDisabled = $derived(
    chatbot.status !== 'complete' || (step === 'vote' && voteData.selected === undefined)
  )

  function onLike(data: ExtendedLikeData) {
    console.log('onLike', data)
    canVote = false
  }

  function onRetry(data: UndoRetryData) {
    console.log('onRetry', data)
  }

  function onPromptSubmit() {
    console.log('onPromptSubmit', prompt)
  }

  function onRevealModels() {
    console.log('revealModels')
    if (canVote === false || step === 'vote') {
      step = 'reveal'
    } else {
      step = 'vote'
    }
  }
</script>

<div id="chat-area">
  <ChatBot
    disabled={chatbotDisabled}
    show_copy_all_button={false}
    value={chatbot.messages}
    pending_message={chatbot.status === 'pending'}
    generating={chatbot.status === 'generating'}
    {onLike}
    {onRetry}
    autoscroll={true}
    {layout}
    {placeholder}
  />
</div>

{#if step === 'vote'}
  <VoteArea bind:value={voteData} />
{/if}

<div id="send-area" class="flex flex-col items-center gap-3 px-4 py-3 md:px-[20%]">
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

  <button disabled={revealDisabled} class="btn purple-btn w-full md:w-fit" onclick={onRevealModels}>
    {m['chatbot.revealButton']()}
  </button>
</div>

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
