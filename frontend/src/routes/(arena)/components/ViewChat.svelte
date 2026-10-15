<script lang="ts">
  import { resolve } from '$app/paths'
  import { Button, Icon, Link, Tooltip } from '$components/dsfr'
  import TextPrompt from '$components/TextPrompt.svelte'
  import { getComparison, getModeInfos } from '$lib/chatService.svelte'
  import { MAX_TURNS_PER_COMPARISON } from '$lib/generated/constants'
  import { m } from '$lib/i18n/messages'
  import { onDestroy } from 'svelte'
  import { GroupedMessages, PauseNotice, PromptWarningModal, RevealArea, VoteModal } from '.'
  import LimitCard from './LimitCard.svelte'
  import { pauseTitle, resetTime, spoken } from './resetTime'

  let {
    comparisonId,
    runAfterAcceptance
  }: {
    comparisonId: string
    runAfterAcceptance: (action: () => unknown | Promise<unknown>) => Promise<void>
  } = $props()

  const comparator = $derived(getComparison(comparisonId))

  let prompt = $state('')
  let voteReminder = $state(false)
  let voteReminderTimeout: ReturnType<typeof setTimeout> | undefined

  const modeInfos = getModeInfos()
  const mode = $derived(modeInfos.find((mode) => mode.value === comparator.comparison?.mode)!)

  const canContinue = $derived(
    !comparator.loading &&
      comparator.status == 'complete' &&
      !!comparator.comparison?.turns.every((turn) => !!turn.choice)
  )

  // The server refuses a turn past the cap: say so before anyone types it.
  const turnsLeft = $derived(MAX_TURNS_PER_COMPARISON - (comparator.comparison?.turns.length ?? 0))
  const atTurnCap = $derived(
    turnsLeft <= 0 && !comparator.loading && comparator.status !== 'generating'
  )
  // Two turns before the cap, once the vote is in: the person is about to
  // type again.
  const turnsHint = $derived.by(() => {
    if (!canContinue || turnsLeft > 2 || turnsLeft <= 0) return undefined
    if (turnsLeft === 1) return m['arene.limits.turns.last']()
    return m['arene.limits.turns.left']({ count: turnsLeft })
  })

  function onReveal() {
    if (comparator.canReveal) comparator.reveal()
    else remindToVote()
  }

  // Focus sits in the send area. A panel that takes the place of the text box
  // then takes focus too, which would otherwise fall to the page; after a
  // vote it leaves focus on the vote.
  let sendAreaFocused = $state(false)

  function onSendAreaFocusOut(e: FocusEvent) {
    const area = e.currentTarget as HTMLElement
    const left = e.target as Node
    if (area.contains(e.relatedTarget as Node | null)) return
    // Some browsers send focusout when the focused text box is removed: that
    // is the case to keep, told apart once the removal is done.
    setTimeout(() => {
      if (left.isConnected) sendAreaFocused = area.contains(document.activeElement)
    })
  }

  async function onPromptSubmit() {
    await runAfterAcceptance(async () => {
      const success = await comparator.ask(prompt)
      if (success) {
        prompt = ''
      }
    })
  }

  async function onSendAnyway() {
    const success = await comparator.sendAnyway()
    if (success) {
      prompt = ''
    }
  }

  function remindToVote() {
    const turn = comparator.comparison?.turns.findLast((currentTurn) => !currentTurn.choice)
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

  // Screen readers get milestones, not tokens: the streaming answers are no
  // longer inside a live region, so this sentence is the only thing spoken.
  // 'pending' is skipped because Pending.svelte already announces it.
  const announcement = $derived.by(() => {
    // A pause that shows after a turn or a vote takes the text box away
    // without moving focus, so it is told here. One met on a send takes focus.
    if (comparator.pause && !comparator.pauseFromSend && !sendAreaFocused) {
      const reset = resetTime(comparator.pause.resets_at)
      return spoken(pauseTitle(reset), reset)
    }
    switch (comparator.status) {
      case 'generating':
        return m['chatbot.announce.generating']()
      case 'complete':
        return m['chatbot.announce.ready']()
      default:
        return ''
    }
  })

  // Compute second header height for autoscrolling
  let footer = $state<HTMLElement>()
  let footerSize: number = $derived(footer ? footer.offsetHeight : 0)

  function onResize() {
    footerSize = footer ? footer.offsetHeight : 0
  }
</script>

<svelte:window onresize={onResize} />

<div style="--footer-size: {footerSize}px;" class="flex grow flex-col">
  <!-- Present from first render: a live region only announces what lands in it after it exists. -->
  <p role="status" class="sr-only">{announcement}</p>

  <div
    id="chat-area"
    role="region"
    aria-label={m['chatbot.conversation']()}
    class="flex grow flex-col"
  >
    {#each comparator.comparison?.turns ?? [] as turn, idx (turn.id)}
      <GroupedMessages
        {turn}
        disabled={comparator.status !== 'complete' ||
          idx !== (comparator.comparison?.turns.length ?? 0) - 1}
        error={comparator.error}
        onVote={comparator.vote}
        onRetry={comparator.retry}
        autoScroll={!comparator.comparison?.revealed}
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

  {#if comparator.status === 'revealed' && comparator.comparison?.reveal_data}
    {#key comparisonId}
      <RevealArea data={comparator.comparison.reveal_data} />
    {/key}
    <!-- FIXME in case of disabled llm: explain why no reveal + cannot continue -->
  {:else if !comparator.comparison.revealed}
    <div
      bind:this={footer}
      onfocusin={() => (sendAreaFocused = true)}
      onfocusout={onSendAreaFocusOut}
      id="send-area"
      class={[
        '-bottom-24 md:bottom-0 gap-3 px-4 py-3 md:px-[20%] z-2 mt-auto flex flex-col items-center bg-linear-(--my-gradient)',
        // A notice that long must not cover the conversation on a phone.
        { sticky: !comparator.pause && !atTurnCap }
      ]}
    >
      {#if atTurnCap}
        <LimitCard
          id="turns-full-notice"
          icon="i-ri-chat-check-line"
          text={m['arene.limits.turns.full']({ max: MAX_TURNS_PER_COMPARISON })}
          focusTitle={sendAreaFocused}
        >
          {#snippet title()}
            {m['arene.limits.turns.fullTitle']()}
          {/snippet}
          {#snippet actions()}
            <Button
              text={m['chatbot.revealButton']()}
              size="sm"
              class="w-full!"
              onclick={onReveal}
            />
            <Link
              button
              variant="secondary"
              size="sm"
              href={resolve('/')}
              text={m['header.chatbot.newDiscussion']()}
              class="w-full!"
            />
          {/snippet}
        </LimitCard>
      {:else if comparator.pause}
        <PauseNotice
          pause={comparator.pause}
          {onReveal}
          failed={!!comparator.error}
          focusTitle={comparator.pauseFromSend || sendAreaFocused}
        />
      {:else}
        <!-- Hidden until the limits are read: a pause would take its place. -->
        <div class={['w-full', { 'cl-limits-pending invisible': !comparator.limitsRead }]}>
          <TextPrompt
            id="chatbot-prompt"
            bind:value={prompt}
            label={m['chatbot.continuePrompt']()}
            placeholder={m['chatbot.continuePrompt']()}
            bind:error={comparator.promptError}
            hint={comparator.busyHint ?? turnsHint}
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
        </div>
      {/if}

      {#if voteReminder}
        <p role="status" class="fr-message fr-message--info mb-0! text-center">
          {m['vote.continueReminder']()}
        </p>
      {/if}

      {#if !comparator.pause && !atTurnCap}
        <Button
          text={m['chatbot.revealButton']()}
          aria-disabled={!comparator.canReveal}
          size="sm"
          icon="arrow-up-circle-line"
          class="md:w-fit! lh-none! w-full!"
          onclick={onReveal}
        />
      {/if}
    </div>
  {/if}
</div>

<VoteModal />

<PromptWarningModal
  warnings={comparator.promptWarnings}
  onProceed={onSendAnyway}
  onEdit={comparator.dismissWarnings}
/>

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
