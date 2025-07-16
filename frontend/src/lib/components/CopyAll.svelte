<script lang="ts">
  import type { ChatMessage } from '$lib/chatService.svelte'
  import IconButton from '$lib/components/IconButton.svelte'
  import { Check, Copy } from '@gradio/icons'
  import { onDestroy } from 'svelte'

  let copied = false
  export let value: ChatMessage[] | null

  let timer: number

  function copy_feedback(): void {
    copied = true
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      copied = false
    }, 1000)
  }

  const copy_conversation = (): void => {
    if (value) {
      const conversation_value = value
        .map((message) => `${message.role}: ${message.content}`)
        .join('\n\n')

      navigator.clipboard.writeText(conversation_value).catch((err) => {
        console.error('Failed to copy conversation: ', err)
      })
    }
  }

  async function handle_copy(): Promise<void> {
    if ('clipboard' in navigator) {
      copy_conversation()
      copy_feedback()
    }
  }

  onDestroy(() => {
    if (timer) clearTimeout(timer)
  })
</script>

<IconButton
  Icon={copied ? Check : Copy}
  on:click={handle_copy}
  label={copied ? 'Copied conversation' : 'Copy conversation'}
></IconButton>
