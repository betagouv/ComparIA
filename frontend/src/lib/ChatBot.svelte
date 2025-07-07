<script lang="ts">
  import { chatbot } from '$lib/chatService.svelte'
  import ChatBot from '$lib/components/ChatBot.svelte'
  import TextPrompt from '$lib/components/TextPrompt.svelte'
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

  let prompt = $state('')

  function onLike(data: ExtendedLikeData) {
    console.log('onLike', data)
  }

  function onRetry(data: UndoRetryData) {
    console.log('onRetry', data)
  }

  function onPromptSubmit() {
    console.log('onPromptSubmit', prompt)
  }

  function onRevealModels() {
    console.log('revealModels')
  }
</script>

<div id="chat-area">
  <ChatBot
    disabled={chatbot.status !== 'complete'}
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

<div id="send-area" class="flex flex-col items-center gap-3 px-4 py-3 md:px-[20%]">
  <div class="flex w-full flex-col gap-3 md:flex-row">
    <TextPrompt
      id="chatbot-prompt"
      bind:value={prompt}
      label="Continuer à discuter avec les deux modèles d'IA"
      placeholder="Continuer à discuter avec les deux modèles d'IA"
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
      Envoyer
    </button>
  </div>

  <button
    disabled={chatbot.status !== 'complete'}
    class="btn purple-btn w-full md:w-fit"
    onclick={onRevealModels}
  >
    Passer à la révélation des modèles
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
