<script lang="ts">
  import Markdown from '$components/markdown/MarkdownCode.svelte'
  import type { UserMessage } from '$lib/chatService.svelte'
  import { WebSearchResults } from '.'

  export type MessageUserProps = {
    id: string
    message: UserMessage
  }

  let { id, message }: MessageUserProps = $props()
</script>

<div class="message-user md:ms-auto md:max-w-3/5 rounded-2xl px-5 py-3 bg-light-info">
  <Markdown message={message.user_content} kind="user" />

  {#if message.web_search_results?.length}
    <WebSearchResults {id} results={message.web_search_results} />
  {/if}
</div>

<style>
  .message-user :global(p:last-of-type) {
    margin: 0;
  }
</style>
