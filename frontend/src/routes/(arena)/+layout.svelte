<script lang="ts">
  import { afterNavigate } from '$app/navigation'
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

  let mainEl: HTMLElement | undefined = $state()
  let routeAnnouncement = $state('')

  afterNavigate((navigation) => {
    // skip first load, and skip in-page hash/replaceState navigations (e.g. arena chat)
    if (navigation.type === 'enter') return
    if (navigation.from?.url.pathname === navigation.to?.url.pathname) return

    mainEl?.focus()
    // Page name only. The full title repeats the site name on every
    // navigation, which is a lot to sit through when it is read aloud.
    routeAnnouncement = document.title.split(' - ')[0]
  })

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

  <!-- tabindex="0", not -1: this element is the page's scroll container, so a
       keyboard user has to be able to reach it to scroll a long page that has
       no links in it. It doubles as the target focused after navigation. The
       lint rule below cannot see that it scrolls. -->
  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
  <main
    id="contenu"
    class="lg:max-h-screen lg:overflow-y-auto cl-main w-full"
    tabindex="0"
    bind:this={mainEl}
  >
    {@render children()}
  </main>
</div>

<p role="status" class="sr-only">{routeAnnouncement}</p>

<SignInModal />

<style>
  /* No ring when script parks focus here after a navigation, but a real one
     when the user tabs to it: :focus-visible does not match programmatic
     focus on a non-interactive element. */
  .cl-main:focus {
    outline: none;
  }

  .cl-main:focus-visible {
    outline: 2px solid var(--outline-color);
    outline-offset: -2px;
  }

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
