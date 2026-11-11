<script lang="ts">
  import { page } from '$app/state'
  import Dropdown from '$components/Dropdown.svelte'
  import { Button, Icon, Tooltip } from '$components/dsfr'
  import TextPrompt from '$components/TextPrompt.svelte'
  import ToolCard from '$components/ToolCard.svelte'
  import { getComparison, getModeInfos } from '$lib/chatService.svelte'
  import type { ToolPublic } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import { onDestroy } from 'svelte'
  import { GroupedMessages, PromptWarningModal, RevealArea, VoteModal } from '.'

  let {
    comparisonId,
    runAfterAcceptance
  }: {
    comparisonId: string
    runAfterAcceptance: (action: () => unknown | Promise<unknown>) => Promise<void>
  } = $props()

  const comparator = $derived(getComparison(comparisonId))

  // The picker lives on the prompt view, which is gone once a conversation has
  // started. Without this the selection silently disappears from view.
  const toolLabels = $derived(
    new Map(((page.data.tools ?? []) as ToolPublic[]).map((tool) => [tool.key, tool.label]))
  )
  const activeTools = $derived(
    (comparator.comparison?.enabled_tools ?? []).map((key) => ({
      key,
      label: toolLabels.get(key) ?? key
    }))
  )

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
          <div class="cg-border rounded-lg! py-2 px-3 grow border-dashed!">
            <p class="mb-1! text-xs! font-bold">{m['chatbot.parameters']()}</p>
            <div class="text-xs gap-2 flex">
              <div class="cg-border rounded-lg! px-2 py-1">
                <Icon icon={mode.icon} size="xs" class="text-primary" />
                {mode.title}
                <Tooltip id="mode-desc" text={mode.description} size="xs" />
              </div>
              <Dropdown
                id="dropdown-tools"
                label={m['chatbot.tools.enabled']()}
                buttonClass="fr-select text-xs! ps-2! pe-8! py-1! shadow-none! bg-transparent! cg-border rounded-lg!"
              >
                {#snippet buttonLabel(label)}
                  <Icon icon="i-ri-tools-line" class="text-primary" size="xs" />
                  {label}
                {/snippet}
                <ul class="m-0 p-2 gap-1 flex list-none flex-col">
                  {#each activeTools as tool (tool.key)}
                    <li class="m-0! p-0">
                      <ToolCard {tool} size="xs" />
                    </li>
                  {/each}
                </ul>
              </Dropdown>
            </div>
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
        class="md:w-fit! lh-none! w-full!"
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
