<script lang="ts">
  import ChatBot from '$lib/components/ChatBot.svelte'
  import type { ExtendedLikeData, Message, NormalisedMessage } from '$lib/types'
  import type { UndoRetryData } from '$lib/utils'
  import { update_messages } from '$lib/utils'
  import type { LoadingStatus } from '@gradio/statustracker'

  export let elem_id = ''
  export let elem_classes: string[] = []
  export let visible = true
  export let value: Message[] = []
  export let interactive = true
  export let root: string
  export let _selectable = true
  export let likeable = true
  export let rtl = false
  export let show_copy_button = true
  export let show_copy_all_button = false
  export let sanitize_html = true
  export let layout: 'bubble' | 'panel' = 'bubble'
  export const type: 'tuples' | 'messages' = 'messages'
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

  let _value: NormalisedMessage[] = []
  $: _value = update_messages(value, _value, root)

  export let like_user_message = false
  export let loading_status: LoadingStatus | undefined = undefined
  export let placeholder: string | null = null

  function onLike(data: ExtendedLikeData) {
    console.log('onLike', data)
  }

  function onRetry(data: UndoRetryData) {
    console.log('onRetry', data)
  }
</script>

<div class="wrapper {elem_classes}" id={elem_id} class:hidden={visible === false}>
  <ChatBot
    selectable={_selectable}
    {likeable}
    disabled={!interactive}
    {show_copy_all_button}
    value={_value}
    {latex_delimiters}
    {render_markdown}
    pending_message={loading_status?.status === 'pending'}
    generating={loading_status?.status === 'generating'}
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
    {root}
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
