<script lang="ts">
  import { goto } from '$app/navigation'
  import { page } from '$app/state'
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

  const tabs = [
    { href: '/admin/branding', label: 'Branding' },
    { href: '/admin', label: 'Users' },
    { href: '/admin/content', label: 'Content' },
  ]
</script>

{#if ready}
  <div class="min-h-screen bg-gray-50">
    <header class="border-b border-gray-200 bg-white px-6 py-3 flex items-center justify-between">
      <span class="text-sm font-medium text-gray-500">ComparIA</span>
      <nav class="flex gap-1">
        {#each tabs as tab}
          <a
            href={tab.href}
            class="rounded px-4 py-1.5 text-sm font-medium no-underline transition-colors
              {page.url.pathname === tab.href
              ? 'bg-gray-900 text-white'
              : 'text-gray-600 hover:bg-gray-100'}"
          >
            {tab.label}
          </a>
        {/each}
      </nav>
    </header>

    {@render children()}
  </div>
{/if}
