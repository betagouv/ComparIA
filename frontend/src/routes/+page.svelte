<script lang="ts">
  import Chatbots from '$lib/Chatbots.svelte'
  import FirstScreen from '$lib/FirstScreen.svelte'
  import { currentScreen } from '$lib/stores'
</script>

{#if $currentScreen === 'FirstScreen'}
  <FirstScreen />
{:else}
  <Chatbots />
{/if}
