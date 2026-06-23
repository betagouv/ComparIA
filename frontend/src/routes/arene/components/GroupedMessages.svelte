<script lang="ts">
  import Pending from '$components/Pending.svelte'
  import SideSwitcher from '$components/SideSwitcher.svelte'
  import type { AnyAPIVote, ComparisonTurn } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { m } from '$lib/i18n/messages'
  import { type Snippet } from 'svelte'
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
</script>

<div class="grouped-messages px-4 py-2 md:py-5 md:px-8 xl:px-16 gap-2 md:gap-5 flex flex-col">
  <div class="md:flex">
    {@render children?.()}

    <MessageUser id={`user-${turn.id}`} message={turn.user_msg} />
  </div>
  <div
    class="grouped-responses flex flex-col"
    class:generating={turn.status === 'pending' || turn.status === 'generating'}
    {@attach scrollTo}
  >
    {#if turn.status === 'pending'}
      <Pending message={m['chatbot.loading']()} class="m-auto" />
    {:else if turn.status === 'error' && error}
      <ErrorDisplay {error} class="mt-10" {onRetry} />
    {:else}
      <SideSwitcher>
        <div class="gap-4 sm:gap-6 md:w-full flex">
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
      </SideSwitcher>
    {/if}

    {#if turn.status === 'complete' && !turn.choice}
      <VoteSelect
        id="vote-select-{turn.id}"
        onVote={(choice) => onVote({ turn_id: turn.id, choice })}
      />
    {/if}
  </div>
</div>
