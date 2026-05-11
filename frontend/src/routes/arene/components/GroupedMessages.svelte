<script lang="ts">
  import { Button } from '$components/dsfr'
  import Pending from '$components/Pending.svelte'
  import type { AnyAPIVote, Bot, ComparisonTurn } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { m } from '$lib/i18n/messages'
  import { onMount, type Snippet } from 'svelte'
  import { ErrorDisplay, MessageBot, MessageUser, VoteSelect } from '.'

  let {
    turn,
    disabled,
    error,
    onVote,
    onRetry,
    children
  }: {
    turn: ComparisonTurn
    disabled: boolean
    error?: string
    onVote: (data: AnyAPIVote) => void
    onRetry: () => void
    children: Snippet<[]> | undefined
  } = $props()

  let userBlockElem = $state<HTMLDivElement>()
  let userMessageSize = $state(0)
  let scrolledModel = $state<Bot>('a')
  let scrollableElem = $state<HTMLDivElement>()

  onMount(() => {
    userMessageSize = userBlockElem!.offsetHeight
  })

  function doScroll() {
    scrollableElem?.scrollTo({ left: scrolledModel === 'a' ? scrollableElem?.scrollWidth : 0 })
    scrolledModel = scrolledModel === 'a' ? 'b' : 'a'
  }
</script>

<div
  class="grouped-messages px-4 py-5 md:px-8 xl:px-16 flex flex-col"
  style="--message-size: {userMessageSize}px;"
  {@attach scrollTo}
>
  <div class="mb-5 md:flex" bind:this={userBlockElem}>
    {@render children?.()}

    <MessageUser message={turn.user_msg} />
  </div>
  {#if turn.status === 'pending'}
    <Pending message={m['chatbot.loading']()} class="m-auto" />
  {:else if turn.status === 'error' && error}
    <ErrorDisplay {error} class="mt-10" {onRetry} />
  {:else}
    <div class="min-h-0 relative flex max-w-full">
      <div class="flex w-full overflow-hidden" bind:this={scrollableElem}>
        <div class="gap-6 md:w-full flex">
          {#if turn.a.llm_msg && turn.b.llm_msg}
            <MessageBot
              id="{turn.id}-a"
              turnSide={turn.a}
              bot="a"
              choice={turn.choice}
              {disabled}
              onVoteAnnotate={(data) => onVote({ turn_id: turn.id, ...data })}
            />

            <MessageBot
              id="{turn.id}-b"
              turnSide={turn.b}
              bot="b"
              choice={turn.choice}
              {disabled}
              onVoteAnnotate={(data) => onVote({ turn_id: turn.id, ...data })}
            />
          {/if}
        </div>
      </div>

      {#each ['a', 'b'] as const as pos (pos)}
        <Button
          text={m[pos === 'b' ? 'actions.scrollRight' : 'actions.scrollLeft']()}
          icon={pos === 'b' ? 'arrow-right-line' : 'arrow-left-line'}
          iconOnly
          variant="tertiary"
          class={[
            'bg-white! md:hidden! absolute top-1/2 inline-flex -translate-y-1/2',
            { 'hidden!': pos === scrolledModel, 'left-0': pos === 'a', 'right-0': pos === 'b' }
          ]}
          onclick={() => doScroll()}
        />
      {/each}
    </div>
  {/if}

  {#if turn.status === 'complete' && !turn.choice}
    <VoteSelect
      id="vote-select-{turn.id}"
      onVote={(choice) => onVote({ turn_id: turn.id, choice })}
    />
  {/if}
</div>
