<script lang="ts">
  import IconButton from '$components/IconButton.svelte'
  import { m } from '$lib/i18n/messages'
  import { copyToClipboard } from '$lib/utils/commons'
  import { onDestroy } from 'svelte'

  let {
    value,
    // What the button announces before and after copying; a message by default.
    labels = { do: m['actions.copyMessage.do'](), done: m['actions.copyMessage.done']() }
  }: { value: string; labels?: { do: string; done: string } } = $props()

  let copied = $state(false)
  let timer: number

  onDestroy(() => {
    if (timer) clearTimeout(timer)
  })

  function showFeedback(): void {
    copied = true
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => (copied = false), 2000) as unknown as number
  }

  async function onCopy(): Promise<void> {
    copyToClipboard(value).then(showFeedback)
  }
</script>

<IconButton
  onclick={onCopy}
  label={copied ? labels.done : labels.do}
  icon={copied ? 'i-ri-check-line' : 'i-ri-file-copy-line'}
/>
