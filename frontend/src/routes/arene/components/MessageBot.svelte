<script lang="ts">
  import Copy from '$components/Copy.svelte'
  import { Icon } from '$components/dsfr'
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import Pending from '$components/Pending.svelte'
  import type { ChatMessage, OnReactionFn, ReactionPref } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'
  import { LikeDislike, LikePanel } from '.'

  export type MessageBotProps = {
    message: ChatMessage<'assistant'>
    generating?: boolean
    disabled?: boolean
    onReactionChange: OnReactionFn
  }

  let {
    message,
    generating = false,
    disabled = false,
    onReactionChange
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
  <div
    class="message-bot cg-border relative flex h-full flex-col overflow-scroll rounded-lg! bg-white px-5"
  >
    <div>
      <div class="sticky top-0 z-2 flex items-center bg-white pt-7 pb-5">
        <div class="c-bot-disk-{bot}"></div>
        <h3 class="ms-2! mb-0! text-base!">{m[`models.names.${bot}`]()}</h3>
      </div>

      {#if message.reasoning != ''}
        <section class="fr-accordion mb-8 py-2">
          <div class="fr-highlight ms-0! ps-0!">
            <h3 class="fr-accordion__title ms-1!">
              <button
                type="button"
                class="fr-accordion__btn bg-transparent! text-primary!"
                aria-expanded="true"
                aria-controls="reasoning-{message.metadata.bot}"
              >
                <Icon icon="brain" class="me-1 text-primary" />
                {#if message.content === '' && generating}
                  {m['chatbot.reasoning.inProgress']()}
                {:else}
                  {m['chatbot.reasoning.finished']()}
                {/if}
              </button>
            </h3>
            <div
              id="reasoning-{message.metadata.bot}"
              class="fr-collapse m-0! p-0! text-sm text-[#8B8B8B]"
            >
              <div class="px-5 py-4">
                {@html sanitize(message.reasoning.split('\n').join('<br>'))}
              </div>
            </div>
          </div>
        </section>
      {/if}

      <Markdown message={message.content} chatbot />

      {#if generating && message.isLast}
        <Pending message={m['chatbot.loading']()} />
      {/if}
    </div>

    <div class="sticky bottom-0 mt-auto flex bg-white py-3">
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
    <div class="cg-border mt-3 rounded-lg! border-dashed! bg-white p-5">
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
  .message-bot {
    --extra-margin: 2.5rem;
    height: calc(
      100vh - var(--second-header-size) - var(--footer-size) - var(--message-size) -
        var(--extra-margin)
    );
    min-height: 50vh;
  }
  @media (min-width: 48em) {
    .message-bot {
      --extra-margin: 3.5rem;
    }
  }
</style>
