<script lang="ts">
  import { goto } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Button, Icon, Tooltip } from '$components/dsfr'
  import TextPrompt from '$components/TextPrompt.svelte'
  import { getComparison, modeInfos } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { onDestroy } from 'svelte'
  import { GroupedMessages, RevealArea, VoteModal } from '.'

  let {
    comparisonId,
    runAfterAcceptance
  }: {
    comparisonId: string
    runAfterAcceptance: (action: () => unknown | Promise<unknown>) => Promise<void>
  } = $props()

  const comparator = $derived(getComparison(comparisonId))

  $effect(() => {
    if (!comparator.comparison) {
      goto(resolve('/arene'))
    }
  })

  let prompt = $state('')
  let voteReminder = $state(false)
  let voteReminderTimeout: ReturnType<typeof setTimeout> | undefined

  const mode = $derived(modeInfos.find((mode) => mode.value === comparator.comparison.mode)!)

  const canContinue = $derived(
    !comparator.loading &&
      comparator.status == 'complete' &&
      comparator.comparison.turns.every((turn) => !!turn.choice)
  )

  async function onPromptSubmit() {
    await runAfterAcceptance(async () => {
      const success = await comparator.ask(prompt)
      if (success) {
        prompt = ''
      }
    })
  }

  function remindToVote() {
    const turn = comparator.comparison.turns.findLast((currentTurn) => !currentTurn.choice)
    if (!turn) return

    voteReminder = true
    clearTimeout(voteReminderTimeout)
    voteReminderTimeout = setTimeout(() => (voteReminder = false), 5000)

    requestAnimationFrame(() => {
      const voteArea = document.getElementById(`vote-select-${turn.id}`)
      if (!voteArea) return

      voteArea.classList.remove('cl-vote-nudge')
      void voteArea.offsetWidth
      voteArea.classList.add('cl-vote-nudge')
      voteArea.scrollIntoView({ behavior: 'smooth', block: 'center' })
      voteArea.querySelector<HTMLButtonElement>('button')?.focus({ preventScroll: true })
    })
  }

  onDestroy(() => clearTimeout(voteReminderTimeout))

  // Compute second header height for autoscrolling
  let footer = $state<HTMLElement>()
  let footerSize: number = $derived(footer ? footer.offsetHeight : 0)

  function onResize() {
    footerSize = footer ? footer.offsetHeight : 0
  }
</script>

<svelte:window onresize={onResize} />

<div style="--footer-size: {footerSize}px;" class="flex grow flex-col">
  <div
    id="chat-area"
    role="log"
    aria-label={m['chatbot.conversation']()}
    aria-live="polite"
    class="flex grow flex-col"
  >
    {#each comparator.comparison.turns as turn, idx (turn.id)}
      <GroupedMessages
        {turn}
        disabled={comparator.status !== 'complete' ||
          idx !== comparator.comparison.turns.length - 1}
        error={comparator.error}
        onVote={comparator.vote}
        onRetry={comparator.retry}
        autoScroll={!comparator.comparison.revealed}
      >
        {#if idx === 0}
          <div
            class="cg-border md:me-3 rounded-lg! bg-white py-1 text-sm mb-3 md:mb-0 px-10 md:py-3 min-w-fit self-start border-dashed! text-center"
          >
            <Icon icon={mode.icon} size="sm" class="text-primary" />
            <strong>{mode.title}</strong>
            <Tooltip id="mode-desc" text={mode.description} size="xs" />
          </div>
        {/if}
      </GroupedMessages>
    {/each}
  </div>

  {#if comparator.status === 'revealed' && comparator.comparison.reveal_data}
    {#key comparisonId}
      <RevealArea data={comparator.comparison.reveal_data} />
    {/key}
  {:else}
    <div
      bind:this={footer}
      id="send-area"
      class="-bottom-24 md:bottom-0 gap-3 px-4 py-3 md:px-[20%] sticky z-2 mt-auto flex flex-col items-center bg-linear-(--my-gradient)"
    >
      <TextPrompt
        id="chatbot-prompt"
        bind:value={prompt}
        label={m['chatbot.continuePrompt']()}
        placeholder={m['chatbot.continuePrompt']()}
        bind:error={comparator.promptError}
        hideLabel
        submitBtn
        submitDisabled={!canContinue || prompt === ''}
        size="md"
        rows={3}
        maxRows={4}
        onSubmit={onPromptSubmit}
        onSubmitBlocked={remindToVote}
        onFocus={() => window.scrollTo(0, document.body.scrollHeight)}
        class="mb-0! w-full"
      />

      {#if voteReminder}
        <p role="status" class="fr-message fr-message--info mb-0! text-center">
          {m['vote.continueReminder']()}
        </p>
      {/if}

      <Button
        text={m['chatbot.revealButton']()}
        aria-disabled={!canContinue}
        size="sm"
        icon="arrow-up-circle-line"
        class="md:w-fit! lh-none! w-full!"
        onclick={() => (canContinue ? comparator.reveal() : remindToVote())}
      />
    </div>
  {/if}
</div>

<VoteModal />

<style>
  #send-area {
    background: linear-gradient(
      180deg,
      var(--cg-very-light-grey) 0%,
      var(--blue-france-950-100) 100%
    );
  }

  :global(#chat-area .grouped-messages) {
    :global(.grouped-responses) {
      max-height: calc(100vh - 2rem);
      scroll-margin-top: calc(var(--second-header-size) + 2rem);
      min-height: 400px;

      @media (min-width: 48em) and (min-height: 48em) {
        max-height: calc(100vh - var(--footer-size) - 2rem);
      }
    }

    :global(&:last-of-type .grouped-responses) {
      max-height: calc(100vh - 6rem);

      @media (min-width: 48em) and (min-height: 48em) {
        max-height: calc(100vh - var(--footer-size) - 4rem);
      }

      &.generating {
        height: calc(100vh - 6rem);

        @media (min-width: 48em) and (min-height: 48em) {
          height: calc(100vh - var(--footer-size) - 4rem);
        }
      }
    }
  }
</style>
