<script lang="ts">
  import { page } from '$app/state'
  import NavBar, { type NavLink } from '$components/header/NavBar.svelte'
  import { initComparisonsContext } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'

  let { children } = $props()

  // NavBar's logout button needs a comparisons context; the admin area never
  // displays the history itself (NavBar skips it when isAdmin).
  initComparisonsContext([])

  const navLinks: NavLink[] = $derived([
    {
      label: m['admin.nav.customization'](),
      href: '/admin/customization',
      icon: 'i-ri-palette-line'
    },
    {
      label: m['admin.nav.locales'](),
      href: '/admin/locales',
      icon: 'i-ri-translate-2'
    },
    {
      label: m['admin.nav.authentification'](),
      href: '/admin/authentification',
      icon: 'i-ri-fingerprint-line'
    },
    {
      label: m['admin.nav.legal'](),
      href: '/admin/legal',
      icon: 'i-ri-file-shield-2-line',
      isCurrent: () =>
        page.url.pathname.startsWith('/admin/legal') ||
        page.url.pathname === '/admin/conditions-participation'
    },
    {
      label: m['admin.nav.users'](),
      href: '/admin/utilisateurs',
      icon: 'i-ri-user-settings-line'
    },
    {
      label: m['admin.nav.suggestions'](),
      href: '/admin/suggestions',
      icon: 'i-ri-lightbulb-line'
    },
    {
      label: m['admin.nav.voteTags'](),
      href: '/admin/vote-tags',
      icon: 'i-ri-price-tag-3-line'
    },
    {
      label: m['admin.nav.promptChecks'](),
      href: '/admin/prompt-checks',
      icon: 'i-ri-shield-check-line'
    },
    {
      label: m['admin.nav.publishing'](),
      href: '/admin/publication',
      icon: 'i-ri-upload-cloud-line'
    },
    {
      label: m['admin.nav.llms'](),
      href: '/admin/llms/llms',
      icon: 'i-ri-ai-agent-line',
      isCurrent: () => page.url.pathname.includes('/admin/llms')
    },
    {
      label: m['actions.returnArena'](),
      href: '/',
      icon: 'i-ri-arrow-left-line'
    }
  ])
</script>

<div
  class="lg:fixed lg:inset-0 lg:w-full lg:h-[100dvh] lg:overflow-hidden lg:bg-very-light-primary! lg:flex min-h-screen"
>
  <NavBar {navLinks} isAdmin />

  <main class="lg:h-[100dvh] lg:overflow-y-auto bg-white w-full">
    {@render children()}
  </main>
</div>
