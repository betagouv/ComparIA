<script lang="ts">
  import IconButton from '$components/IconButton.svelte'
  import type { AnyMessage } from '$lib/chatService.svelte'
  import { copyToClipboard } from '$lib/utils/commons'
  import { onDestroy } from 'svelte'

  let { value }: { value: AnyMessage[] } = $props()

  let copied = $state(false)
  let timer: number

  onDestroy(() => {
    if (timer) clearTimeout(timer)
  })

  function showFeedback(): void {
    copied = true
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => (copied = false), 2000)
  }

  async function onCopy(): Promise<void> {
    if (value) {
      const conversationValue = value
        .map((message) => `${message.role}: ${message.content}`)
        .join('\n\n')

      await copyToClipboard(conversationValue)
        .catch((err) => {
          console.error('Failed to copy conversation: ', err)
        })
        .then(showFeedback)
    }
  }
</script>

<IconButton
  icon={copied ? 'check-line' : 'copy'}
  onclick={onCopy}
  label={copied ? 'Copied conversation' : 'Copy conversation'}
/>
