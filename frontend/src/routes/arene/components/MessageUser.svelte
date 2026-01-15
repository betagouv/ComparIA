<script lang="ts">
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import type { UserMessage } from '$lib/chatService.svelte'
  import { onMount } from 'svelte'

  export type MessageUserProps = {
    message: UserMessage
    size: number
  }

  let { message, size = $bindable() }: MessageUserProps = $props()

  let elem = $state<HTMLDivElement>()

  onMount(() => {
    size = elem!.offsetHeight
  })
</script>

<div
  bind:this={elem}
  class="message-user md:max-w-3/5 mb-4 mt-5 rounded-2xl px-5 py-3 md:mb-8 md:ms-auto bg-[--grey-950-100]"
>
  <Markdown message={message.content} kind="user" />

  <!-- <div class="message-buttons-right">
    <Copy value={message.content} />
  </div> -->
</div>

<style>
  .message-user :global(p:last-of-type) {
    margin: 0;
  }
</style>
