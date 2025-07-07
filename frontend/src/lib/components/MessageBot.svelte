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
  let comment = $state(message.comment)
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
      text: "Qu'avez-vous apprécié dans la réponse ?",
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

  const onSelection = (value: string[]) => {
    selection = value
    onReaction('like', {
      ...message,
      prefs: selection
    })
  }

  const onComment = (value: string) => {
    onReaction('comment', {
      ...message,
      commented: comment !== '',
      comment
    })
  }
</script>

<div class="message-bot flex flex-col">
  {selection}
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
        commented={message.commented}
        {modalId}
        {...currentReaction}
        {onSelection}
        model={bot.toUpperCase()}
      />
    </div>

    <!-- Weird way to catch the comment if not validated but modal closed -->
    <dialog
      aria-labelledby="{modalId}-label"
      id={modalId}
      class="fr-modal"
      onblur={() => onComment(comment)}
      onkeydown={(e) => {
        if (e.key === 'Escape') {
          onComment(comment)
        }
      }}
    >
      <div class="fr-container fr-container--fluid fr-container-md">
        <div class="fr-grid-row fr-grid-row--center">
          <div class="fr-col-12 fr-col-md-8 fr-col-lg-6">
            <div class="fr-modal__body">
              <div class="fr-modal__header">
                <button
                  class="fr-btn--close fr-btn"
                  title="Fermer la fenêtre modale"
                  aria-controls={modalId}
                  onclick={() => onComment(comment)}>Fermer</button
                >
              </div>
              <div class="fr-modal__content">
                <p id="{modalId}-label" class="modal-title">Ajouter des commentaires</p>
                <div>
                  <textarea
                    placeholder="Vous pouvez ajouter des précisions sur cette réponse du modèle {bot.toUpperCase()}"
                    class="fr-input"
                    rows="4"
                    bind:value={comment}
                  ></textarea>
                  <button
                    aria-controls={modalId}
                    class="btn purple-btn"
                    onclick={() => onComment(comment)}>Envoyer</button
                  >
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </dialog>
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

  .modal-title {
    font-weight: 700;
    font-size: 1.1em;
  }

  .fr-modal__content .purple-btn {
    float: right;
    margin: 2em 0 !important;
  }
</style>
