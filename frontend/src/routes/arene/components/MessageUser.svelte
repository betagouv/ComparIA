<script lang="ts">
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import type { ChatMessage } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'

  export type MessageUserProps = {
    message: ChatMessage<'user'>
  }

  let { message }: MessageUserProps = $props()
</script>

<div
  {@attach scrollTo}
  class="message-user md:max-w-3/5 mb-4 mt-5 rounded-2xl px-5 py-3 md:mb-8 md:ms-auto"
>
  <Markdown message={message.content} />

  <!-- <div class="message-buttons-right">
    <Copy value={message.content} />
  </div> -->
</div>

<style>
  .message-user {
    background-color: var(--grey-950-100);
    scroll-margin-top: calc(var(--second-header-size) + 1rem);
  }

  .message-user :global(p:last-of-type) {
    margin: 0;
  }
</style>
