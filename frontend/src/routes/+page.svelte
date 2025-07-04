<script lang="ts">
  import ChatBot from '$lib/ChatBot.svelte'
  import { runChatBots, type ModeAndPromptData } from '$lib/chatService.svelte'
  import DropDown from '$lib/DropDown.svelte'
  import { state } from '$lib/state.svelte'

  async function onSubmit(args: ModeAndPromptData) {
    await runChatBots(args)
  }
</script>

{#if state.currentScreen === 'initial'}
  <DropDown {onSubmit} />
{:else}
  <ChatBot></ChatBot>
{/if}
