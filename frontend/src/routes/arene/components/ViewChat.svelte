<script lang="ts">
  import { Button, Icon, Tooltip } from '$components/dsfr'
  import Footer from '$components/Footer.svelte'
  import Pending from '$components/Pending.svelte'
  import TextPrompt from '$components/TextPrompt.svelte'
  import { getComparison, modeInfos } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { m } from '$lib/i18n/messages'
  import { ErrorDisplay, GroupedMessages, RevealArea } from '.'

  let { comparisonId }: { comparisonId: string } = $props()

  const comparator = $derived(getComparison(comparisonId))

  let prompt = $state('')

  const mode = $derived(modeInfos.find((mode) => mode.value === comparator.comparison.mode)!)

  const canContinue = $derived(
    !comparator.loading &&
      comparator.status == 'complete' &&
      comparator.comparison.turns.every((turn) => !!turn.choice)
  )

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
    class="pb-7 flex grow flex-col"
  >
    {#each comparator.comparison.turns as turn, idx (turn.id)}
      <GroupedMessages
        {turn}
        disabled={comparator.status !== 'complete' ||
          idx !== comparator.comparison.turns.length - 1}
        onVote={comparator.vote}
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

    {#if comparator.error}
      <ErrorDisplay
        error={comparator.error}
        class={{ 'mt-10': comparator.comparison.turns.length > 1 }}
        onRetry={() => comparator.retry()}
      />
    {:else if comparator.loading}
      <Pending message={m['chatbot.loading']()} class="m-auto" {@attach scrollTo} />
    {/if}
  </div>

  {#if comparator.status === 'revealed' && comparator.comparison.reveal}
    <RevealArea data={comparator.comparison.reveal} />
    <Footer />
  {:else}
    <div
      bind:this={footer}
      id="send-area"
      class="bg-very-light-grey bottom-0 gap-3 px-4 py-3 md:px-[20%] sticky z-2 mt-auto flex flex-col items-center"
    >
      <div class="gap-3 md:flex-row flex w-full flex-col">
        <TextPrompt
          id="chatbot-prompt"
          bind:value={prompt}
          label={m['chatbot.continuePrompt']()}
          placeholder={m['chatbot.continuePrompt']()}
          error={comparator.promptError}
          hideLabel
          rows={1}
          maxRows={4}
          onSubmit={() => comparator.ask(prompt)}
          class="mb-0! w-full"
        />

        <Button
          id="send-btn"
          text={m['words.send']()}
          disabled={!canContinue || prompt === ''}
          class="md:w-auto! md:self-end! w-full!"
          onclick={() => comparator.ask(prompt)}
        />
      </div>

      <Button
        text={m['chatbot.revealButton']()}
        disabled={!canContinue}
        class="md:w-fit! w-full!"
        onclick={() => comparator.reveal()}
      />
    </div>
  {/if}
</div>

<style>
  :global(#chat-area:has(+ #send-area) .grouped-messages:last-of-type) {
    min-height: calc(100vh - var(--second-header-size) - var(--footer-size));
    scroll-margin-top: calc(var(--second-header-size));

    @media (min-width: 48em) {
      height: calc(100vh - var(--second-header-size) - var(--footer-size));
    }
  }
</style>
