<script lang="ts">
  import Pending from '$components/Pending.svelte'
  import type { AnyAPIVote, ComparisonTurn } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { m } from '$lib/i18n/messages'
  import { onMount, type Snippet } from 'svelte'
  import { MessageBot, MessageUser, VoteSelect } from '.'

  let {
    turn,
    disabled,
    onVote,
    children
  }: {
    turn: ComparisonTurn
    disabled: boolean
    onVote: (data: AnyAPIVote) => void
    children: Snippet<[]> | undefined
  } = $props()

  let userBlockElem = $state<HTMLDivElement>()
  let userMessageSize = $state(0)

  onMount(() => {
    userMessageSize = userBlockElem!.offsetHeight
  })
</script>

<div
  class="grouped-messages not-last:mb-15 px-4 py-5 md:px-8 xl:px-16 flex flex-col"
  style="--message-size: {userMessageSize}px;"
  {@attach scrollTo}
>
  <div class="mb-5 md:flex" bind:this={userBlockElem}>
    {@render children?.()}

    <MessageUser message={turn.user_msg} />
  </div>
  {#if turn.status === 'pending'}
    <Pending message={m['chatbot.loading']()} class="m-auto" />
  {:else}
    <div class="gap-10 md:flex-row md:gap-6 min-h-0 flex flex-col">
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
  {/if}

  {#if turn.status === 'complete' && !turn.choice}
    <VoteSelect
      id="vote-select-{turn.id}"
      onVote={(choice) => onVote({ turn_id: turn.id, choice })}
    />
  {/if}
</div>
