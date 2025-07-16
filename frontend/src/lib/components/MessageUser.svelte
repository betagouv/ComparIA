<script lang="ts">
  import type { ChatMessage } from '$lib/chatService.svelte'
  import Markdown from '$lib/components/markdown/MarkdownCode.svelte'
  import { noop } from '$lib/utils/commons'

  export type MessageUserProps = {
    message: ChatMessage<'user'>
    onLoad: () => void
  }

  let { message, onLoad = noop }: MessageUserProps = $props()
</script>

<div class="message-user mb-4 mt-5 rounded-2xl px-5 py-3 md:mb-8">
  <Markdown message={message.content} on:load={onLoad} />

  <!-- <div class="message-buttons-right">
    <Copy value={message.content} />
  </div> -->
</div>

<style>
  .message-user {
    background-color: var(--grey-950-100);
  }

  .message-user :global(p:last-of-type) {
    margin: 0;
  }

  @media (min-width: 48em) {
    .message-user {
      width: 60%;
      margin-left: auto;
    }
  }
</style>
