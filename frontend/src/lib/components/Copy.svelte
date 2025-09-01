<script lang="ts">
  import IconButton from '$components/IconButton.svelte'
  import { m } from '$lib/i18n/messages'
  import { copyToClipboard } from '$lib/utils/commons'
  import { onDestroy } from 'svelte'

  let { value }: { value: string } = $props()

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
    copyToClipboard(value).then(showFeedback)
  }
</script>

<IconButton
  onclick={onCopy}
  label={m[`actions.copyMessage.${copied ? 'done' : 'do'}`]()}
  icon={copied ? 'check-line' : 'copy'}
/>
