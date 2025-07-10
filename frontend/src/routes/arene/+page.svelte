<script lang="ts">
  import ChatBot from '$lib/ChatBot.svelte'
  import { runChatBots, type ModeAndPromptData } from '$lib/chatService.svelte'
  import DropDown from '$lib/DropDown.svelte'
  import { state } from '$lib/state.svelte'
  import { onMount } from 'svelte'

  onMount(async () => {
    // FIXME import only modal? Or create custom component
    // @ts-ignore - DSFR module import
    await import('@gouvfr/dsfr/dist/dsfr/dsfr.module.min.js')
  })

  async function onSubmit(args: ModeAndPromptData) {
    await runChatBots(args)
  }
</script>

{#if state.currentScreen === 'initial'}
  <DropDown {onSubmit} />
{:else}
  <ChatBot></ChatBot>
{/if}
