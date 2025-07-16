<script lang="ts">
  import IconButton from '$lib/components/IconButton.svelte'
  import { m } from '$lib/i18n/messages'
  import { onDestroy } from 'svelte'

  let copied = false
  export let value: string
  let timer: NodeJS.Timeout

  function copy_feedback(): void {
    copied = true
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      copied = false
    }, 2000)
  }

  async function handle_copy(): Promise<void> {
    if ('clipboard' in navigator) {
      await navigator.clipboard.writeText(value)
      copy_feedback()
    } else {
      const textArea = document.createElement('textarea')
      textArea.value = value

      textArea.style.position = 'absolute'
      textArea.style.left = '-999999px'

      document.body.prepend(textArea)
      textArea.select()

      try {
        document.execCommand('copy')
        copy_feedback()
      } catch (error) {
        console.error(error)
      } finally {
        textArea.remove()
      }
    }
  }

  onDestroy(() => {
    if (timer) clearTimeout(timer)
  })
</script>

<IconButton
  onclick={handle_copy}
  label={m[`actions.copyMessage.${copied ? 'done' : 'do'}`]()}
  icon={copied ? 'check-line' : 'copy'}
/>
