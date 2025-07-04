<script lang="ts">
  import ChatBot from '$lib/ChatBot.svelte'
  import { runChatBots } from '$lib/chatService.svelte'
  import DropDown from '$lib/DropDown.svelte'
  import type { ModeAndPromptData } from '$lib/utils-customdropdown'

  let currentScreen = $state<'FirstScreen' | 'Chatbots'>('FirstScreen')

  async function onSubmit(args: ModeAndPromptData) {
    currentScreen = 'Chatbots'

    await runChatBots(args)
  }
</script>

{#if currentScreen === 'FirstScreen'}
  <DropDown {onSubmit} />
{:else}
  <ChatBot></ChatBot>
{/if}
