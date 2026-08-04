<script lang="ts">
  import { NavBar } from '$components/header'
  import { getAuthContext, userAllowed } from '$lib/auth.svelte.js'
  import { initComparisonsContext } from '$lib/chatService.svelte.js'
  import SignInModal from '$lib/components/SignInModal.svelte'
  import { m } from '$lib/i18n/messages'
  import { setVoteTagsContext } from '$lib/voteTags'

  let { children, data } = $props()

  initComparisonsContext(data.comparisons)
  setVoteTagsContext(data.voteTags)
  const auth = getAuthContext()

  const navLinks = $derived(
    [
      { href: '/arene', label: m['header.chatbot.newDiscussion'](), icon: 'i-ri-chat-new-line' },
      { href: '/arene/ranking', label: m['seo.titles.ranking'](), icon: 'i-ri-trophy-line' },
      { href: '/arene/modeles', label: m['seo.titles.modeles'](), icon: 'i-ri-stack-line' },
      { href: '/admin', role: 'admin', label: m['admin.panelLink'](), icon: 'i-ri-admin-line' }
    ].filter((link) => userAllowed(auth, link.role))
  )
</script>

<div class="lg:flex min-h-screen">
  <NavBar {navLinks} />

  <main class="lg:max-h-screen lg:overflow-y-auto w-full">
    {@render children()}
  </main>
</div>

<SignInModal />
