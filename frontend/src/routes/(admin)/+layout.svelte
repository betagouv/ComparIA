<script lang="ts">
  import { goto } from '$app/navigation'
  import { page } from '$app/state'
  import NavBar, { type NavLink } from '$components/header/NavBar.svelte'
  import { initAuth, isAdmin } from '$lib/auth.svelte'
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

  const navLinks: NavLink[] = [
    { label: 'Utilisateurs', href: '/admin', icon: 'i-ri-user-settings-line' },
    {
      label: 'Configuration auth',
      href: '/admin/configuration/auth',
      icon: 'i-ri-fingerprint-line'
    },
    {
      label: 'LLMs',
      href: '/admin/llms/llms',
      icon: 'i-ri-ai-agent-line',
      isCurrent: () => page.url.pathname.includes('/admin/llms')
    }
  ]
</script>

{#if ready}
  <div class="lg:flex min-h-screen">
    <NavBar {navLinks} isAdmin />

    <main class="lg:max-h-screen lg:overflow-y-auto w-full">
      {@render children()}
    </main>
  </div>
{/if}
