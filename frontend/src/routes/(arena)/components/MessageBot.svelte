<script lang="ts">
  import Copy from '$components/Copy.svelte'
  import { Button, Icon } from '$components/dsfr'
  import { MarkdownCode as Markdown } from '$components/markdown'
  import type {
    APIVoteAnnotate,
    Bot,
    ComparisonTurnSide,
    TurnChoice
  } from '$lib/chatService.svelte'
  import { useScroller } from '$lib/helpers/useScroller.svelte'
  import { m } from '$lib/i18n/messages'
  import { VoteAnnotate } from '.'
  import AgentTrace from './AgentTrace.svelte'
  import type { APITrace } from './toolActivity'

  export type MessageBotProps = {
    id: string
    turnSide: ComparisonTurnSide
    bot: Bot
    choice: TurnChoice | null
    disabled?: boolean
    onVoteAnnotate: (data: Omit<APIVoteAnnotate, 'turn_id'>) => void
  }

  let { id, turnSide, bot, choice, disabled = false, onVoteAnnotate }: MessageBotProps = $props()

  const prefKind = $derived.by(() => {
    if (!choice || choice == 'idk') return null
    return choice == 'both_good' || choice == `${bot}_better` ? 'positive' : 'negative'
  })

  const message = $derived(turnSide.llm_msg!)

  const trace = $derived((message.agent_trace as APITrace) ?? [])
  const generating = $derived(turnSide.status === 'generating')

  let annotations = $derived({
    keyword_annotations: turnSide.keyword_annotations,
    custom_annotation: turnSide.custom_annotation
  })

  const scroller = useScroller()

  function onScrollClick() {
    scroller[scroller.isAtBottom ? 'scrollToTop' : 'scrollToBottom']()
  }
</script>

<div class="md:w-full md:min-w-0 md:flex-1 flex w-[80vw] flex-col">
  <div
    class={[
      'message-bot cg-border rounded-lg! bg-white flex h-full flex-col overflow-hidden',
      {
        'outline-2 -outline-offset-2': !!prefKind,
        'outline-red': prefKind === 'negative',
        'outline-green': prefKind === 'positive'
      }
    ]}
  >
    <div class="px-4 py-2 flex items-center">
      <div class="c-bot-disk-{bot}"></div>
      <h3 class="ms-2! mb-0! text-sm! me-auto">{m[`models.names.${bot}`]()}</h3>
      <Copy value={message.content} />
    </div>

    <!-- Long answers scroll inside this box. Without a tab stop, a keyboard
         user cannot reach the part below the fold. -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
    <div
      class="flex h-full flex-col overflow-scroll"
      tabindex="0"
      role="group"
      aria-label={m[`models.names.${bot}`]()}
      {@attach scroller.attach}
    >
      <div class="px-4 pb-4">
        {#if trace.length || message.reasoning_content}
          <AgentTrace
            {id}
            {trace}
            reasoning={message.reasoning_content ?? ''}
            pending={generating && !message.content.trim()}
          />
        {/if}

        <Markdown message={message.content} chatbot />
      </div>

      {#if scroller.canScroll || generating}
        <div
          class="bottom-0 mx-1 pb-3 to-white sticky mt-auto flex justify-center bg-gradient-to-b from-transparent to-90%"
        >
          {#snippet loadingIcon()}
            <div
              class="loading-icon size-6 text-primary relative inline-block"
              aria-label={m['chatbot.loading']()}
            >
              {#each [1, 2, 3, 4] as dot (dot)}
                <div
                  class={[
                    'top-2 absolute size-[6px] rounded-full bg-current ease-[cubic-bezier(0,1,1,0)]',
                    {
                      'left-0 [animation:grow_0.6s_infinite]': dot === 1,
                      'left-0 [animation:move_0.6s_infinite]': dot === 2,
                      'left-[9px] [animation:move_0.6s_infinite]': dot === 3,
                      'left-[18px] [animation:shrink_0.6s_infinite]': dot === 4
                    }
                  ]}
                ></div>
              {/each}
            </div>
          {/snippet}

          {#if scroller.canScroll}
            <Button
              id="scroll-btn"
              variant="tertiary"
              class={['p-2! not-hover:bg-white! min-h-0!', { generating }]}
              onclick={onScrollClick}
            >
              <span class="sr-only">
                {m[scroller.isAtBottom ? 'actions.scrollToTop' : 'actions.scrollToBottom']()}
              </span>

              {#if generating}
                {@render loadingIcon()}
              {/if}
              <Icon
                icon={scroller.isAtBottom ? 'i-ri-arrow-up-line' : 'i-ri-arrow-down-line'}
                block
                class={{ hidden: generating }}
              />
            </Button>
          {:else if generating}
            {@render loadingIcon()}
          {/if}
        </div>
      {/if}
    </div>

    {#if prefKind}
      <VoteAnnotate
        id="vote-annotate-{id}"
        bind:annotations
        kind={prefKind}
        {disabled}
        onUpdate={(annotations) => onVoteAnnotate({ pos: bot, ...annotations })}
      />
    {/if}
  </div>
</div>

<style>
  :global(#scroll-btn.generating) {
    &:focus,
    &:hover {
      .loading-icon {
        display: none;
      }
      :global(.hidden) {
        display: block;
      }
    }
  }

  @keyframes -global-grow {
    0% {
      transform: scale(0);
    }
    100% {
      transform: scale(1);
    }
  }

  @keyframes -global-move {
    0% {
      transform: translate(0, 0);
    }
    100% {
      transform: translate(9px, 0);
    }
  }

  @keyframes -global-shrink {
    0% {
      transform: scale(1);
    }
    100% {
      transform: scale(0);
    }
  }
</style>
