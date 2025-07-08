<script lang="ts">
  import Copy from '$lib/components/Copy.svelte'
  import LikeDislike from '$lib/components/LikeDislike.svelte'
  import LikePanel from '$lib/components/LikePanel.svelte'
  import Markdown from '$lib/components/markdown/MarkdownCode.svelte'
  import ThumbDownActive from '$lib/icons/ThumbDownActive.svelte'
  import ThumbUpActive from '$lib/icons/ThumbUpActive.svelte'
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

  const reactions = {
    like: {
      text: "Qu'avez-vous apprécié dans la réponse ?",
      Icon: ThumbUpActive,
      choices: [
        ['Utile', 'useful'],
        ['Complète', 'complete'],
        ['Créative', 'creative'],
        ['Mise en forme claire', 'clear-formatting']
      ] as [string, string][]
    },
    dislike: {
      text: 'Pourquoi la réponse ne convient-elle pas ?',
      Icon: ThumbDownActive,
      choices: [
        ['Incorrecte', 'incorrect'],
        ['Superficielle', 'superficial'],
        ['Instructions non suivies', 'instructions-not-followed']
      ] as [string, string][]
    }
  }

  const currentReaction = $derived<(typeof reactions)['like' | 'dislike'] | null>(
    selected ? reactions[selected] : null
  )

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

<div class="message-bot flex flex-col">
  <div class="message-bot-{bot} c-border flex h-full flex-col rounded-2xl px-5 pb-3 pt-7">
    <div>
      <div class="mb-5 flex items-center">
        <div class="disk"></div>
        <h3 class="mb-0! ms-1!">{bot === 'a' ? 'Modèle A' : 'Modèle B'}</h3>
      </div>

      <Markdown message={message.content} chatbot on:load={onLoad} />
    </div>

    <div class="mt-auto flex">
      <Copy value={message.content} />

      <div class="ms-auto flex gap-2">
        <LikeDislike disabled={generating || disabled} {onLikeDislikeSelected} />
      </div>
    </div>
  </div>

  {#if selected && currentReaction}
    <div class="mt-3">
      <LikePanel
        show={true}
        comment={message.comment}
        {modalId}
        {...currentReaction}
        {onSelectionChange}
        {onCommentChange}
        model={bot.toUpperCase()}
      />
    </div>
  {/if}
</div>

<style>
  .message-bot .disk {
    width: 26px;
    height: 26px;
    border-radius: 50%;
  }

  .message-bot-a .disk {
    background-color: var(--bot-a-color);
  }
  .message-bot-b .disk {
    background-color: var(--bot-b-color);
  }
</style>
