<script lang="ts">
  import type { ChatMessage, OnReactionFn, ReactionPref } from '$lib/chatService.svelte'
  import Copy from '$lib/components/Copy.svelte'
  import LikeDislike from '$lib/components/LikeDislike.svelte'
  import LikePanel from '$lib/components/LikePanel.svelte'
  import Markdown from '$lib/components/markdown/MarkdownCode.svelte'
  import Pending from '$lib/components/Pending.svelte'
  import { m } from '$lib/i18n/messages'
  import { noop } from '$lib/utils/commons'

  export type MessageBotProps = {
    message: ChatMessage<'assistant'>
    generating?: boolean
    disabled?: boolean
    onReactionChange: OnReactionFn
    onLoad?: () => void
  }

  let {
    message,
    generating = false,
    disabled = false,
    onReactionChange,
    onLoad = noop
  }: MessageBotProps = $props()

  const bot = message.metadata.bot
  const reaction = $state<{
    liked: boolean | null
    prefs: ReactionPref[]
    comment: string
  }>({
    liked: null,
    prefs: [],
    comment: ''
  })

  function onLikedChanged() {
    reaction.prefs = []
    dispatchOnReactionChange('like')
  }

  function dispatchOnReactionChange(kind: 'like' | 'comment') {
    onReactionChange(kind, {
      ...reaction,
      index: message.index,
      value: message.content
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

      {#if generating && message.isLast}
        <Pending />
      {/if}
    </div>

    <div class="mt-auto flex">
      <Copy value={message.content} />

      <div class="ms-auto flex gap-2">
        <LikeDislike
          bind:liked={reaction.liked}
          disabled={generating || disabled}
          onChange={onLikedChanged}
        />
      </div>
    </div>
  </div>

  {#if reaction.liked !== null}
    <div class="message-bot-like-panel mt-3">
      <LikePanel
        kind={reaction.liked ? 'like' : 'dislike'}
        show={true}
        bind:selection={reaction.prefs}
        bind:comment={reaction.comment}
        modalId="modal-prefs-{message.metadata.generation_id}"
        onSelectionChange={() => dispatchOnReactionChange('like')}
        onCommentChange={() => dispatchOnReactionChange('comment')}
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
