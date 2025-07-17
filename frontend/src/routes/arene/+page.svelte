<script lang="ts">
  import ChatBot from '$lib/ChatBot.svelte'
  import { runChatBots, type APIModeAndPromptData } from '$lib/chatService.svelte'
  import DropDown from '$lib/DropDown.svelte'
  import { infos } from '$lib/state.svelte'
  import { onMount } from 'svelte'
  import WelcomeModal from './WelcomeModal.svelte'

  let { data } = $props()

  onMount(async () => {
    // FIXME import only modal? Or create custom component
    // @ts-ignore - DSFR module import
    await import('@gouvfr/dsfr/dist/dsfr/dsfr.module.min.js')
  })

  async function onSubmit(args: APIModeAndPromptData) {
    await runChatBots(args)
  }
</script>

<WelcomeModal />

{#if infos.currentScreen === 'initial'}
  <DropDown {onSubmit} models={data.models} />
{:else}
  <ChatBot></ChatBot>
{/if}
