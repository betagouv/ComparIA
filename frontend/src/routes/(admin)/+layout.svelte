<script lang="ts">
  import { goto } from '$app/navigation'
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
</script>

{#if ready}
  <div class="min-h-screen bg-[--background-alt-grey]">
    <header class="border-b border-[--border-default-grey] bg-white px-6 py-3 flex items-center">
      <span class="fr-text--sm text-[--text-mention-grey] font-medium">ComparIA Admin</span>
    </header>
    {@render children()}
  </div>
{/if}
