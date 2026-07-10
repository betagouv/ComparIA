<script lang="ts">
  import { goto } from '$app/navigation'
  import { page } from '$app/state'
  import NavBar, { type NavLink } from '$components/header/NavBar.svelte'
  import { initAuth, isAdmin } from '$lib/auth.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  let { children } = $props()
  let ready = $state(false)

  onMount(async () => {
    await initAuth()
    if (!isAdmin()) {
      goto('/')
      return
    }
    ready = true
  })

  const navLinks: NavLink[] = $derived([
    {
      label: m['admin.nav.personnalisation'](),
      href: '/admin/personnalisation',
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
      href: '/admin/llms/list',
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

{#if ready}
  <div class="lg:flex min-h-screen">
    <NavBar {navLinks} isAdmin />

    <main class="lg:max-h-screen lg:overflow-y-auto w-full">
      {@render children()}
    </main>
  </div>
{/if}
