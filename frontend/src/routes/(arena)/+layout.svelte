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
      { href: '/', label: m['header.chatbot.newDiscussion'](), icon: 'i-ri-chat-new-line' },
      { href: '/ranking', label: m['seo.titles.ranking'](), icon: 'i-ri-trophy-line' },
      { href: '/modeles', label: m['seo.titles.modeles'](), icon: 'i-ri-stack-line' },
      { href: '/admin', role: 'admin', label: m['admin.panelLink'](), icon: 'i-ri-admin-line' }
    ].filter((link) => userAllowed(auth, link.role))
  )
</script>

<a href="#contenu" class="cl-skip-link">{m['a11y.skipToContent']()}</a>

<div class="lg:flex min-h-screen">
  <NavBar {navLinks} />

  <main id="contenu" class="lg:max-h-screen lg:overflow-y-auto w-full">
    {@render children()}
  </main>
</div>

<SignInModal />

<style>
  .cl-skip-link {
    position: absolute;
    left: -9999px;
    top: 0;
    z-index: 1000;
  }

  .cl-skip-link:focus {
    left: 0;
    padding: 0.5rem 1rem;
    background-color: var(--background-default-grey);
    color: var(--text-title-blue-france);
  }
</style>
