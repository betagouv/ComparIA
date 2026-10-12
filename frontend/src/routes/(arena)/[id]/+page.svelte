<script lang="ts">
  import { goto } from '$app/navigation'
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Link } from '$components/dsfr'
  import { PageLayout } from '$components/layout'
  import { getComparison } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { TOSModal, ViewChat } from '../components'

  const id = $derived(page.params.id)
  const comparator = $derived(getComparison(id))
  const revealed = $derived(comparator.status === 'revealed')

  // Any path the arena doesn't own lands here too (e.g. /arene), so an id with
  // no comparison behind it goes back to the arena instead of rendering a chat.
  $effect(() => {
    if (!comparator.comparison) {
      goto(resolve('/'), { replaceState: true })
    }
  })

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
        href="/"
        text={m['header.chatbot.newDiscussion']()}
        class="text-nowrap"
      />
    </div>
  {/snippet}

  {#if comparator.comparison}
    <ViewChat comparisonId={comparator.comparisonId!} {runAfterAcceptance} />
  {/if}
</PageLayout>
