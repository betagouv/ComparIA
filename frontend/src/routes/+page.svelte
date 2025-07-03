<script lang="ts">
  import { api, parseGradioResponse, type GradioResponse } from '$lib/api'
  import DropDown from '$lib/DropDown.svelte'
  import type { ModeAndPromptData } from '$lib/utils-customdropdown'

  let currentScreen = $state<'FirstScreen' | 'Chatbots'>('FirstScreen')
  const conversation = $state<{
    chatbot1: string
    chatbot2: string
  }>({ chatbot1: '', chatbot2: '' })

  async function onSubmit(args: ModeAndPromptData) {
    currentScreen = 'Chatbots'
    const job = await api.submit('/add_first_text', { model_dropdown_scoped: args })
    console.log('aaaa')
    for await (const message of job) {
      if (message.type === 'data') {
        const messages = parseGradioResponse(message as GradioResponse)
        console.log('message', messages)
        conversation.chatbot1 = messages[1].content
        conversation.chatbot2 = messages[2].content
      }
    }
  }
</script>

{#if currentScreen === 'FirstScreen'}
  <DropDown {onSubmit} />
{:else}
  <div>
    {conversation.chatbot1}
  </div>
  <div>
    {conversation.chatbot2}
  </div>
{/if}
