<script lang="ts">
  import { currentScreen } from '$lib/stores';
  import Chatbots from '$lib/Chatbots.svelte';

  import FirstScreen from '$lib/FirstScreen.svelte';
</script>

{#if $currentScreen === 'FirstScreen'}
  <FirstScreen />
{:else}
  <Chatbots />
{/if}
