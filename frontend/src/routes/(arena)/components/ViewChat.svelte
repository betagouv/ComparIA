<script lang="ts">
  import { goto } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { Button, Icon, Tooltip } from '$components/dsfr'
  import TextPrompt from '$components/TextPrompt.svelte'
  import { getComparison, modeInfos } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
<<<<<<< HEAD:frontend/src/routes/(arena)/components/ViewChat.svelte
  import { onDestroy } from 'svelte'
  import { GroupedMessages, PromptWarningModal, RevealArea, VoteModal } from '.'
=======
  import { GroupedMessages, RevealArea, VoteModal } from '.'
  import { onDestroy } from 'svelte'
>>>>>>> 10ea04a6 (fix(ui): affine les retours visuels de l’arène):frontend/src/routes/arene/components/ViewChat.svelte

  let {
    comparisonId,
    runAfterAcceptance
  }: {
    comparisonId: string
    runAfterAcceptance: (action: () => unknown | Promise<unknown>) => Promise<void>
  } = $props()

  const comparator = $derived(getComparison(comparisonId))

<<<<<<< HEAD:frontend/src/routes/(arena)/components/ViewChat.svelte
  // A comparison that isn't in the store sends us back to the arena. The
  // redirect only lands on the next tick, so everything below has to survive
  // a render with no comparison rather than throw on the way out.
  $effect(() => {
    if (!comparator.comparison) {
      goto(resolve('/'))
    }
  })
=======
  let prompt = $state('')
  let voteReminder = $state(false)
  let voteReminderTimeout: ReturnType<typeof setTimeout> | undefined
>>>>>>> 10ea04a6 (fix(ui): affine les retours visuels de l’arène):frontend/src/routes/arene/components/ViewChat.svelte

  let prompt = $state('')
  let voteReminder = $state(false)
  let voteReminderTimeout: ReturnType<typeof setTimeout> | undefined

  const mode = $derived(modeInfos.find((mode) => mode.value === comparator.comparison?.mode)!)

  const canContinue = $derived(
    !comparator.loading &&
      comparator.status == 'complete' &&
      !!comparator.comparison?.turns.every((turn) => !!turn.choice)
  )

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
<<<<<<< HEAD:frontend/src/routes/(arena)/components/ViewChat.svelte
    const turn = comparator.comparison?.turns.findLast((currentTurn) => !currentTurn.choice)
=======
    const turn = comparator.comparison.turns.findLast((currentTurn) => !currentTurn.choice)
>>>>>>> 10ea04a6 (fix(ui): affine les retours visuels de l’arène):frontend/src/routes/arene/components/ViewChat.svelte
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

<<<<<<< HEAD:frontend/src/routes/(arena)/components/ViewChat.svelte
  // Screen readers get milestones, not tokens: the streaming answers are no
  // longer inside a live region, so this sentence is the only thing spoken.
  // 'pending' is skipped because Pending.svelte already announces it.
  const announcement = $derived.by(() => {
    switch (comparator.status) {
      case 'generating':
        return m['chatbot.announce.generating']()
      case 'complete':
        return m['chatbot.announce.ready']()
      default:
        return ''
    }
  })

=======
>>>>>>> 10ea04a6 (fix(ui): affine les retours visuels de l’arène):frontend/src/routes/arene/components/ViewChat.svelte
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
<<<<<<< HEAD:frontend/src/routes/(arena)/components/ViewChat.svelte
        class="md:w-fit! lh-none! w-full!"
=======
        class={['md:w-fit! lh-none! w-full!', { 'cursor-not-allowed opacity-50': !canContinue }]}
>>>>>>> 10ea04a6 (fix(ui): affine les retours visuels de l’arène):frontend/src/routes/arene/components/ViewChat.svelte
        onclick={() => (canContinue ? comparator.reveal() : remindToVote())}
      />
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
