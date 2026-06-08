<script lang="ts">
  import { NavBar } from '$components/header'

  let { children } = $props()
</script>

<div class="lg:flex min-h-screen">
  <NavBar />

  <main class="lg:max-h-screen w-full overflow-y-auto">
    {@render children()}
  </main>
</div>
