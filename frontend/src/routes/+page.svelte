<script lang="ts">
  import ChatBot from '$lib/ChatBot.svelte'
  import { runChatBots } from '$lib/chatService.svelte'
  import DropDown from '$lib/DropDown.svelte'
  import { state } from '$lib/state.svelte'
  import type { ModeAndPromptData } from '$lib/utils-customdropdown'

  async function onSubmit(args: ModeAndPromptData) {
    await runChatBots(args)
  }
</script>

{#if state.currentScreen === 'initial'}
  <DropDown {onSubmit} />
{:else}
  <ChatBot></ChatBot>
{/if}
