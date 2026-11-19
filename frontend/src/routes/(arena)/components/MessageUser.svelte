<script lang="ts">
  import { MarkdownCode as Markdown } from '$components/markdown'
  import type { UserMessage } from '$lib/chatService.svelte'

  export type MessageUserProps = {
    id: string
    message: UserMessage
  }

  let { id, message }: MessageUserProps = $props()
</script>

<div {id} class="message-user md:ms-auto md:max-w-3/5 rounded-2xl px-5 py-3 bg-light-primary">
  <Markdown message={message.content} kind="user" />
</div>

<style>
  .message-user :global(p:last-of-type) {
    margin: 0;
  }
</style>
