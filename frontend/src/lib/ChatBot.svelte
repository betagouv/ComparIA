<script lang="ts">
  import ChatBot from '$lib/components/ChatBot.svelte'
  import type { ExtendedLikeData } from '$lib/types'
  import type { UndoRetryData } from '$lib/utils'
  import { chatbot } from '$lib/chatService.svelte'

  let rtl = false
  let layout: 'bubble' | 'panel' = 'bubble'
  let latex_delimiters: {
    left: string
    right: string
    display: boolean
  }[] = []
  let placeholder: string | null = null

  function onLike(data: ExtendedLikeData) {
    console.log('onLike', data)
  }

  function onRetry(data: UndoRetryData) {
    console.log('onRetry', data)
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

  :global(.progress-text) {
    right: auto;
  }
</style>
