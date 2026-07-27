<script lang="ts">
  import { page } from '$app/state'
  import { Link } from '$components/dsfr'
  import PageLayout from '$components/PageLayout.svelte'
  import { getComparison } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { TOSModal, ViewChat } from '../components'

  const id = $derived(page.params.id)
  const comparator = $derived(getComparison(id))
  const revealed = $derived(comparator.status === 'revealed')

  let tosModal = $state<{
    runAfterAcceptance: (action: () => unknown | Promise<unknown>) => Promise<void>
  }>()

  async function runAfterAcceptance(action: () => unknown | Promise<unknown>): Promise<void> {
    await tosModal?.runAfterAcceptance(action)
  }
</script>

<TOSModal bind:this={tosModal} />

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

  <ViewChat comparisonId={comparator.comparisonId!} {runAfterAcceptance} />
</PageLayout>
