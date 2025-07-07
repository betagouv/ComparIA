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
  <div id="main-chatbot" class="wrapper chatbot">
    <ChatBot
      selectable={true}
      disabled={chatbot.status !== 'complete'}
      show_copy_all_button={false}
      value={chatbot.messages}
      {latex_delimiters}
      render_markdown={true}
      pending_message={chatbot.status === 'pending'}
      generating={chatbot.status === 'generating'}
      {rtl}
      show_copy_button={true}
      like_user_message={false}
      {onLike}
      {onRetry}
      sanitize_html={true}
      line_breaks={true}
      autoscroll={true}
      {layout}
      {placeholder}
      _retryable={false}
      _undoable={false}
      root={chatbot.root}
    />
  </div>
</div>

<div
  id="send-area"
  class="column fr-pt-1w svelte-vt1mxs gap"
  style="flex-grow: 1; min-width: min(320px, 100%);"
>
  <div class="row flex-md-row svelte-1xp0cw7 unequal-height flex-col items-start">
    <div class="form svelte-633qhp" style="flex-grow: 1; min-width: min(160px, 100%);">
      <TextPrompt 
        id="chatbot-prompt"
        bind:value={prompt}
        label="Continuer à discuter avec les deux modèles d'IA"
        placeholder="Continuer à discuter avec les deux modèles d'IA"
        hideLabel
        maxRows={4}
        autofocus
        class="w-full"
        onSubmit={onPromptSubmit}
      />
    </div>

    <button
      id="send-btn"
      disabled={chatbot.status !== 'complete' || prompt === ''}
      onclick={onPromptSubmit}
      class="lg secondary purple-btn fr-ml-md-1w svelte-1ixn6qd w-full grow-0"
    >
      Envoyer
    </button>
  </div>
  <div class="row fr-grid-row fr-grid-row--center svelte-1xp0cw7 unequal-height">
    <button
      disabled={chatbot.status !== 'complete'}
      class="lg secondary fr-col-12 fr-col-md-5 purple-btn fr-mt-1w svelte-1ixn6qd"
      onclick={onRevealModels}
    >
      Passer à la révélation des modèles
    </button>
  </div>
</div>

<style>
  .wrapper {
    display: flex;
    position: relative;
    flex-direction: column;
    align-items: start;
    width: 100%;
    height: 100%;
    flex-grow: 1;
  }
</style>
