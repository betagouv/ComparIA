<script lang="ts">
  import { NavBar } from '$components/header'
  import SignInModal from '$lib/components/SignInModal.svelte'

  let { children } = $props()
</script>

<div class="lg:flex min-h-screen">
  <NavBar />

  <main class="lg:max-h-screen lg:overflow-y-auto w-full">
    {@render children()}
  </main>
</div>

<SignInModal />
