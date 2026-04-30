<script lang="ts">
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import type { UserMessage } from '$lib/chatService.svelte'

  export type MessageUserProps = {
    message: UserMessage
  }

  let { message }: MessageUserProps = $props()
</script>

<div class="message-user md:ms-auto md:max-w-3/5 rounded-2xl px-5 py-3 bg-light-info">
  <Markdown message={message.content} kind="user" />
</div>

<style>
  .message-user :global(p:last-of-type) {
    margin: 0;
  }
</style>
