<script lang="ts">
  import { Link } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { fetchAndSolveSilently } from '$lib/captcha.svelte'
  import { getComparison, initComparisonsContext } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { TOSModal, ViewChat, ViewPrompt } from './components'

  // TODO query user comparisons
  initComparisonsContext([])
  // Start solving Altcha challenge on page load (runs in background)
  fetchAndSolveSilently()

  const comparator = getComparison(undefined)
  const showInitialPrompt = $derived(!comparator.comparisonId)

  const revealed = $derived(comparator.status === 'revealed')
</script>

<TOSModal />

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
        href="../arene/?cgu_acceptees"
        text={m['header.chatbot.newDiscussion']()}
        class="text-nowrap"
      />
    </div>
  {/snippet}

  {#if showInitialPrompt}
    <ViewPrompt
      loading={comparator.loading}
      promptError={comparator.promptError}
      onPrompt={comparator.askFirst}
    />
  {:else}
    <ViewChat comparisonId={comparator.comparisonId!} />
  {/if}
</PageLayout>
