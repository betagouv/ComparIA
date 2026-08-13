<script lang="ts">
  import Pending from '$components/Pending.svelte'
  import SideSwitcher from '$components/SideSwitcher.svelte'
  import type { AnyAPIVote, ComparisonTurn, TurnChoice } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { m } from '$lib/i18n/messages'
  import { tick, type Snippet } from 'svelte'
  import { ErrorDisplay, MessageBot, MessageUser, VoteSelect } from '.'

  let {
    turn,
    disabled,
    error,
    autoScroll,
    onVote,
    onRetry,
    children
  }: {
    turn: ComparisonTurn
    disabled: boolean
    error?: string
    autoScroll?: boolean
    onVote: (data: AnyAPIVote) => void
    onRetry: () => void
    children: Snippet<[]> | undefined
  } = $props()

  // Voting unmounts the fieldset the focused button lives in, which drops focus
  // to <body>: the next Tab restarts at the top of the document, back through
  // both answers. Hand it to whatever the vote just revealed instead.
  async function onChoice(choice: TurnChoice) {
    onVote({ turn_id: turn.id, choice })
    await tick()
    const next =
      document.getElementById(`vote-annotate-${turn.id}-a-comment`) ??
      document.getElementById('chatbot-prompt')
    next?.focus({ preventScroll: true })
  }
</script>

<div class="grouped-messages px-4 py-2 md:py-5 md:px-6 gap-2 md:gap-5 flex flex-col">
  <div class="md:flex">
    {@render children?.()}

    <MessageUser id={`user-${turn.id}`} message={turn.user_msg} />
  </div>
  <div
    class="grouped-responses flex flex-col"
    class:generating={turn.status === 'pending' || turn.status === 'generating'}
    {@attach autoScroll && scrollTo}
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
      <VoteSelect id="vote-select-{turn.id}" onVote={onChoice} />
    {/if}
  </div>
</div>
