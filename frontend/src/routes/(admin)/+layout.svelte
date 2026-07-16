<script lang="ts">
  import { page } from '$app/state'
  import NavBar, { type NavLink } from '$components/header/NavBar.svelte'
  import { m } from '$lib/i18n/messages'

  let { children } = $props()

  const navLinks: NavLink[] = $derived([
    {
      label: m['admin.nav.customization'](),
      href: '/admin/customization',
      icon: 'i-ri-palette-line'
    },
    {
      label: m['admin.nav.authentification'](),
      href: '/admin/authentification',
      icon: 'i-ri-fingerprint-line'
    },
    {
      label: m['admin.nav.users'](),
      href: '/admin/utilisateurs',
      icon: 'i-ri-user-settings-line'
    },
    {
      label: m['admin.nav.llms'](),
      href: '/admin/llms/llms',
      icon: 'i-ri-ai-agent-line',
      isCurrent: () => page.url.pathname.includes('/admin/llms')
    },
    {
      label: m['actions.returnArena'](),
      href: '/arene',
      icon: 'i-ri-arrow-left-line'
    }
  ])
</script>

<div class="lg:flex min-h-screen">
  <NavBar {navLinks} isAdmin />

  <main class="lg:max-h-screen lg:overflow-y-auto w-full">
    {@render children()}
  </main>
</div>
