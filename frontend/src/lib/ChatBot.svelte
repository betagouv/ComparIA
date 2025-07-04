<script lang="ts">
  import ChatBot from '$lib/components/ChatBot.svelte'
  import type { ExtendedLikeData } from '$lib/types'
  import type { UndoRetryData } from '$lib/utils'
  import { chatbot } from '$lib/chatService.svelte'

  export let elem_id = ''
  export let elem_classes: string[] = []
  export let _selectable = true
  export let rtl = false
  export let show_copy_button = true
  export let show_copy_all_button = false
  export let sanitize_html = true
  export let layout: 'bubble' | 'panel' = 'bubble'
  export let render_markdown = true
  export let line_breaks = true
  export let autoscroll = true
  export let _retryable = false
  export let _undoable = false
  export let latex_delimiters: {
    left: string
    right: string
    display: boolean
  }[] = []
  export let like_user_message = false
  export let placeholder: string | null = null

  function onLike(data: ExtendedLikeData) {
    console.log('onLike', data)
  }

  function onRetry(data: UndoRetryData) {
    console.log('onRetry', data)
  }
</script>

<div class="wrapper {elem_classes}" id={elem_id}>
  <ChatBot
    selectable={_selectable}
    disabled={chatbot.status !== 'complete'}
    {show_copy_all_button}
    value={chatbot.messages}
    {latex_delimiters}
    {render_markdown}
    pending_message={chatbot.status === 'pending'}
    generating={chatbot.status === 'generating'}
    {rtl}
    {show_copy_button}
    {like_user_message}
    {onLike}
    {onRetry}
    {sanitize_html}
    {line_breaks}
    {autoscroll}
    {layout}
    {placeholder}
    {_retryable}
    {_undoable}
    root={chatbot.root}
  />
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
