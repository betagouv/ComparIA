<script lang="ts">
  import { goto, preloadData } from '$app/navigation'
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

  const navItems = [
    { label: 'Utilisateurs', href: '/admin' },
    { label: 'Configuration auth', href: '/admin/configuration/auth' },

  ]

  const currentPath = $derived(page.url.pathname)
</script>

{#if ready}
  <div class="min-h-screen bg-[--background-alt-grey] flex flex-col">
    <header class="border-b border-[--border-default-grey] bg-white px-6 py-3 flex items-center">
      <span class="fr-text--sm text-[--text-mention-grey] font-medium">ComparIA Admin</span>
    </header>
    <div class="flex flex-1">
      <nav class="w-56 shrink-0 border-r border-[--border-default-grey] bg-white py-4" aria-label="Navigation admin">
        <ul class="list-none p-0 m-0">
          {#each navItems as item}
            <li>
              <a
                href={item.href}
                class="block px-5 py-2 fr-text--sm no-underline! {currentPath === item.href ? 'font-semibold text-[--text-active-blue-france] bg-[--background-alt-blue-france]' : 'text-[--text-label-grey] hover:bg-[--background-alt-grey]'}"
              >
                {item.label}
              </a>
            </li>
          {/each}
        </ul>
      </nav>
      <main class="flex-1 overflow-auto">
        {@render children()}
      </main>
    </div>
  </div>
{/if}
