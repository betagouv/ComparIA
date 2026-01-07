<script lang="ts">
  import { Button } from '$components/dsfr'
  import Footer from '$components/Footer.svelte'
  import TextPrompt from '$components/TextPrompt.svelte'
  import type { OnReactionFn, RevealData, VoteData } from '$lib/chatService.svelte'
  import {
    arena,
    askChatBots,
    getReveal,
    postVoteGetReveal,
    retryAskChatBots,
    updateReaction
  } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { ChatBot, RevealArea, VoteArea } from '.'

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

  const chatbotDisabled = $derived(arena.chat.status !== 'complete' || step !== 'chat')
  const revealDisabled = $derived(
    arena.chat.status !== 'complete' || (step === 'vote' && voteData.selected === undefined)
  )

  const onReactionChange: OnReactionFn = async (reaction) => {
    canVote = reaction.liked === null
    await updateReaction(reaction)
  }

  function onRetry() {
    retryAskChatBots()
  }

  function onVote() {
    // FIXME if user already react? go to reveal for now
    onRevealModels()
  }

  async function onPromptSubmit() {
    window.scrollTo(0, document.body.scrollHeight)
    await askChatBots(prompt)
    prompt = ''
  }

  async function onRevealModels() {
    // if chat as reactions, no need to show vote
    if (canVote === false) {
      revealData = await getReveal()
      step = 'reveal'
      arena.chat.step = 2
    } else if (step === 'vote') {
      if (!voteData.selected) return
      revealData = await postVoteGetReveal(voteData as Required<VoteData>)
      step = 'reveal'
      arena.chat.step = 2
    } else {
      step = 'vote'
    }
  }

  // Compute second header height for autoscrolling
  let footer = $state<HTMLElement>()
  let footerSize: number = $derived(step && footer ? footer.offsetHeight : 0)

  function onResize() {
    footerSize = footer ? footer.offsetHeight : 0
  }
</script>

<svelte:window onresize={onResize} />

<div style="--footer-size: {footerSize}px;" class="flex grow flex-col">
  <ChatBot
    disabled={chatbotDisabled}
    pending={arena.chat.status === 'pending'}
    generating={arena.chat.status === 'generating'}
    {onReactionChange}
    {onRetry}
    {onVote}
  />

  {#if step === 'vote' || (step === 'reveal' && canVote)}
    <VoteArea bind:value={voteData} disabled={step === 'reveal'} />
  {/if}

  {#if step === 'reveal' && revealData}
    <RevealArea data={revealData} />
    <Footer />
  {:else}
    <div
      bind:this={footer}
      id="send-area"
      class="bottom-0 gap-3 bg-very-light-grey px-4 py-3 md:px-[20%] sticky z-2 mt-auto flex flex-col items-center"
    >
      {#if step === 'chat'}
        <div class="gap-3 md:flex-row flex w-full flex-col">
          <TextPrompt
            id="chatbot-prompt"
            bind:value={prompt}
            label={m['chatbot.continuePrompt']()}
            placeholder={m['chatbot.continuePrompt']()}
            hideLabel
            rows={1}
            maxRows={4}
            onSubmit={onPromptSubmit}
            class="mb-0! w-full"
          />

          <Button
            id="send-btn"
            text={m['words.send']()}
            disabled={arena.chat.status !== 'complete' || prompt === ''}
            class="md:w-auto! md:self-end! w-full!"
            onclick={onPromptSubmit}
          />
        </div>
      {/if}

      <Button
        text={m['chatbot.revealButton']()}
        disabled={revealDisabled}
        class="md:w-fit! w-full!"
        onclick={onRevealModels}
      />
    </div>
  {/if}
</div>
