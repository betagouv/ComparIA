<script lang="ts">
  import { Link } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { fetchAndSolveSilently } from '$lib/captcha.svelte'
  import { getComparison, type APIModeAndPromptData } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import type { PageProps } from './$types'
  import { shouldShowInitialPrompt } from './arenaPageState'
  import { ErrorDisplay, PromptWarningModal, TOSModal, ViewChat, ViewPrompt } from './components'

  let { data }: PageProps = $props()

  // Start solving Altcha challenge on page load (runs in background)
  fetchAndSolveSilently()

  const comparator = getComparison(undefined)
  const showInitialPrompt = $derived(
    shouldShowInitialPrompt(comparator.comparisonId, comparator.comparison)
  )

  const revealed = $derived(comparator.status === 'revealed')

  let tosModal = $state<{
    runAfterAcceptance: (action: () => unknown | Promise<unknown>) => Promise<void>
  }>()

  async function runAfterAcceptance(action: () => unknown | Promise<unknown>): Promise<void> {
    await tosModal?.runAfterAcceptance(action)
  }

  // Kept so the error banner below can resend the exact same prompt when
  // initialization dies before the first turn is shown.
  let lastPromptArgs = $state<APIModeAndPromptData>()

  async function submitInitialPrompt(args: APIModeAndPromptData): Promise<void> {
    lastPromptArgs = args
    await runAfterAcceptance(() => comparator.askFirst(args))
  }
</script>

<TOSModal bind:this={tosModal} />

{#if showInitialPrompt}
  <PromptWarningModal
    warnings={comparator.promptWarnings}
    onProceed={comparator.sendAnyway}
    onEdit={comparator.dismissWarnings}
  />
{/if}

<PageLayout
  seoTitle={m['seo.titles.arene']()}
  title={m[revealed ? 'header.chatbot.reveal.description' : 'seo.titles.arene']()}
  subtitle={revealed ? m['header.chatbot.reveal.subtitle']() : undefined}
  bubble={revealed ? m['header.chatbot.reveal.title']() : undefined}
  class="bg-very-light-grey p-0! relative flex min-h-full flex-col"
  stickyHeader
  headerClass={{ 'sr-only!': !revealed }}
>
  {#snippet header()}
    <div class={['ms-auto hidden items-center', { 'md:block': revealed }]}>
      <Link
        button
        icon="edit-line"
        href="/"
        text={m['header.chatbot.newDiscussion']()}
        class="text-nowrap"
      />
    </div>
  {/snippet}

  {#if showInitialPrompt}
    <!-- The stream died after /add_first_text opened but before the first turn
         rendered: ViewPrompt has no turn to attach the error to, so surface it
         here and let the user resend the prompt they still have typed. -->
    {#if comparator.error && !comparator.loading}
      <ErrorDisplay
        error={comparator.error}
        onRetry={() => {
          if (lastPromptArgs) void submitInitialPrompt(lastPromptArgs)
        }}
      />
    {/if}
    <ViewPrompt
      loading={comparator.loading}
      promptError={comparator.promptError}
      onPrompt={submitInitialPrompt}
      suggestions={data.suggestions.categories}
    />
  {:else}
    <ViewChat comparisonId={comparator.comparisonId!} {runAfterAcceptance} />
  {/if}
</PageLayout>
