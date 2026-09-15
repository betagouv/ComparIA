<script lang="ts">
  import { Button } from '$components/dsfr'
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
    onStop,
    children
  }: {
    turn: ComparisonTurn
    disabled: boolean
    error?: string
    autoScroll?: boolean
    onVote: (data: AnyAPIVote) => Promise<void> | void
    onRetry: () => void
    onStop: () => Promise<void> | void
    children: Snippet<[]> | undefined
  } = $props()

  const running = $derived(turn.status === 'pending' || turn.status === 'generating')
  const answered = $derived(turn.status === 'complete' || turn.status === 'interrupted')

  let responses = $state<HTMLElement>()

  // From the click on Stop until the turn stops running, one way or another.
  // Held here, next to the button: the store behind the conversation view is
  // not the one streaming the first turn, so it cannot tell when to reset.
  let stopping = $state(false)

  async function onStopClick() {
    if (stopping) return
    stopping = true
    try {
      await onStop()
    } catch (err) {
      // The stream is still running; let the user press again.
      stopping = false
      throw err
    }
  }

  // Stopping unmounts the Stop button, which held focus, so the next Tab
  // would restart from the top of the document. Once the 'interrupted' event
  // has landed, hand focus to what the stop revealed: the vote, or Retry when
  // the stop came before a first word and the turn shows as failed. Only
  // after a stop from here: a stopped turn loaded from history keeps focus
  // where it is.
  $effect(() => {
    // Read the status first: it is what the effect has to wake up on.
    if (running || !stopping) return
    stopping = false
    tick().then(() => {
      // VoteSelect renders one grid per breakpoint and hides the other, and
      // focus() on a display:none button is a no-op. jsdom has no layout and
      // no checkVisibility, so there every button counts as visible.
      const choices = responses?.querySelectorAll<HTMLElement>('fieldset[id^=vote-select] button')
      const next =
        [...(choices ?? [])].find((el) => el.checkVisibility?.() ?? true) ??
        responses?.querySelector<HTMLElement>(`#retry-${turn.id}, [role="alert"] button`) ??
        document.getElementById('chatbot-prompt')
      next?.focus({ preventScroll: true })
    })
  })

  // Voting unmounts the fieldset the focused button lives in, which drops focus
  // to <body>: the next Tab restarts at the top of the document, back through
  // both answers. Hand it to whatever the vote just revealed instead.
  //
  // The await matters: turn.choice is only set once the POST comes back, and
  // the annotation box is what that renders. Without it we looked a round trip
  // too early, always missed, and fell through to the prompt box — stepping
  // over the controls the vote had just revealed. Nothing moves before then
  // anyway, since the button keeping focus lives until the same response.
  async function onChoice(choice: TurnChoice) {
    try {
      await onVote({ turn_id: turn.id, choice })
    } finally {
      // Even on a failed vote: the alternative is focus stranded on <body>.
      await tick()
      const next =
        document.getElementById(`vote-annotate-${turn.id}-a-comment`) ??
        document.getElementById('chatbot-prompt')
      next?.focus({ preventScroll: true })
    }
  }
</script>

<div class="grouped-messages px-4 py-2 md:py-5 md:px-6 gap-2 md:gap-5 flex flex-col">
  <div class="md:flex">
    {@render children?.()}

    <MessageUser id={`user-${turn.id}`} message={turn.user_msg} />
  </div>
  <div
    bind:this={responses}
    class="grouped-responses flex flex-col"
    class:generating={running}
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

    {#if running}
      <!-- aria-disabled rather than disabled: the button keeps focus while the
           stop is on its way, and the next Tab still starts from here. -->
      <div class="mt-3 flex justify-center">
        <Button
          id="stop-{turn.id}"
          text={m['chatbot.stop']()}
          icon="stop-circle-line"
          variant="secondary"
          size="sm"
          aria-disabled={stopping}
          onclick={onStopClick}
        />
      </div>
    {:else if turn.status === 'interrupted'}
      <div id="interrupted-{turn.id}" class="mt-3 gap-2 flex flex-col items-center">
        <p role="status" class="fr-message fr-message--info mb-0! text-center">
          {m['chatbot.interrupted.notice']()}
        </p>
        {#if !turn.choice}
          <Button
            id="retry-{turn.id}"
            icon="refresh-line"
            iconPos="right"
            text={m['words.retry']()}
            variant="secondary"
            size="sm"
            onclick={() => onRetry()}
          />
        {/if}
      </div>
    {/if}

    {#if answered && !turn.choice}
      <VoteSelect id="vote-select-{turn.id}" onVote={onChoice} />
    {/if}
  </div>
</div>
