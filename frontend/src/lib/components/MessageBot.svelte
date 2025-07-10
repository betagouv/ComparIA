<script lang="ts">
  import Copy from '$lib/components/Copy.svelte'
  import LikeDislike from '$lib/components/LikeDislike.svelte'
  import LikePanel from '$lib/components/LikePanel.svelte'
  import Markdown from '$lib/components/markdown/MarkdownCode.svelte'
  import Pending from '$lib/components/Pending.svelte'
  import { m } from '$lib/i18n/messages'
  import type { NormalisedMessage } from '$lib/types'
  import { noop } from '$lib/utils/commons'

  export type MessageBotProps = {
    message: NormalisedMessage
    generating?: boolean
    disabled?: boolean
    onReaction: (kind: 'like' | 'comment', message: NormalisedMessage) => void
    onLoad?: () => void
  }

  let {
    message,
    generating = false,
    disabled = false,
    onReaction,
    onLoad = noop
  }: MessageBotProps = $props()

  const bot = message.metadata.bot as 'a' | 'b'
  let modalId = `modal-prefs-${message.index}`

  let selected: 'like' | 'dislike' | null = $state(null)
  let selection: string[] = $state(message.prefs || [])

  const onLikeDislikeSelected = (value: 'like' | 'dislike' | null) => {
    selected = value
    selection = []
    onReaction('like', {
      ...message,
      liked: selected === 'like' || undefined,
      disliked: selected === 'dislike' || undefined,
      prefs: selection
    })
  }

  const onSelectionChange = (value: string[]) => {
    selection = value
    onReaction('like', {
      ...message,
      prefs: selection
    })
  }

  const onCommentChange = (value: string) => {
    onReaction('comment', {
      ...message,
      commented: value !== '',
      comment: value
    })
  }
</script>

<div class="flex flex-col">
  <div class="c-border flex h-full flex-col rounded-2xl px-5 pb-3 pt-7">
    <div>
      <div class="mb-5 flex items-center">
        <div class="c-bot-disk-{bot}"></div>
        <h3 class="mb-0! ms-1!">{m[`models.names.${bot}`]()}</h3>
      </div>

      <Markdown message={message.content} chatbot on:load={onLoad} />

      {#if generating}
        <Pending />
      {/if}
    </div>

    <div class="mt-auto flex">
      <Copy value={message.content} />

      <div class="ms-auto flex gap-2">
        <LikeDislike disabled={generating || disabled} {onLikeDislikeSelected} />
      </div>
    </div>
  </div>

  {#if selected}
    <div class="mt-3 message-bot-like-panel">
      <LikePanel
        kind={selected}
        show={true}
        comment={message.comment}
        {modalId}
        {onSelectionChange}
        {onCommentChange}
        model={bot.toUpperCase()}
      />
    </div>
  {/if}
</div>

<style>
  .message-bot-like-panel {
    padding: 1em 1.5em 1em;
    background-color: white;
    border-color: #e5e5e5;
    border-style: dashed;
    border-width: 1.5px;
    border-radius: 0.25rem;
  }
</style>
