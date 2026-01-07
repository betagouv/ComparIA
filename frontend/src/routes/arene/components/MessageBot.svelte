<script lang="ts">
  import Copy from '$components/Copy.svelte'
  import { Icon } from '$components/dsfr'
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import Pending from '$components/Pending.svelte'
  import type { APIReactionData, ChatMessage, OnReactionFn } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'
  import { LikeDislike, LikePanel } from '.'

  export type MessageBotProps = {
    message: ChatMessage<'assistant'>
    index: number
    generating?: boolean
    disabled?: boolean
    onReactionChange: OnReactionFn
  }

  let {
    message,
    index,
    generating = false,
    disabled = false,
    onReactionChange
  }: MessageBotProps = $props()

  const bot = message.metadata.bot
  const reaction = $state<APIReactionData>({
    index: index,
    bot: message.metadata.bot,
    liked: null,
    prefs: [],
    comment: '',
    value: message.content
  })

  function onLikedChanged() {
    reaction.prefs = []
    dispatchOnReactionChange()
  }

  function dispatchOnReactionChange() {
    onReactionChange({
      ...reaction,
      value: message.content
    })
  }
</script>

<div class="flex flex-col">
  <div
    class="message-bot cg-border rounded-lg! bg-white px-5 relative flex h-full flex-col overflow-scroll"
  >
    <div>
      <div class="top-0 bg-white pb-5 pt-7 sticky z-2 flex items-center">
        <div class="c-bot-disk-{bot}"></div>
        <h3 class="ms-2! mb-0! text-base!">{m[`models.names.${bot}`]()}</h3>
      </div>

      {#if message.reasoning != ''}
        <section class="fr-accordion mb-8 py-2">
          <div class="fr-highlight ms-0! ps-0!">
            <h3 class="fr-accordion__title ms-1!">
              <button
                type="button"
                class="fr-accordion__btn text-primary! bg-transparent!"
                aria-expanded="true"
                aria-controls="reasoning-{message.metadata.generation_id}"
              >
                <Icon icon="i-ri-brain-2-line" class="text-primary me-1" />
                {#if message.content === '' && generating}
                  {m['chatbot.reasoning.inProgress']()}
                {:else}
                  {m['chatbot.reasoning.finished']()}
                {/if}
              </button>
            </h3>
            <div
              id="reasoning-{message.metadata.generation_id}"
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

    <div class="bottom-0 bg-white py-3 sticky mt-auto flex">
      <Copy value={message.content} />

      <div class="gap-2 ms-auto flex">
        <LikeDislike
          bind:liked={reaction.liked}
          disabled={generating || disabled}
          onChange={onLikedChanged}
        />
      </div>
    </div>
  </div>

  {#if reaction.liked !== null}
    <div class="cg-border rounded-lg! mt-3 bg-white p-5 border-dashed!">
      <LikePanel
        id={message.metadata.generation_id}
        kind={reaction.liked ? 'like' : 'dislike'}
        show={true}
        bind:selection={reaction.prefs}
        bind:comment={reaction.comment}
        onSelectionChange={dispatchOnReactionChange}
        onCommentChange={dispatchOnReactionChange}
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
