<script lang="ts">
  import Markdown from '$lib/components/markdown/MarkdownCode.svelte'
  import type { NormalisedMessage } from '$lib/types'
  import { noop } from '$lib/utils/commons'

  export type MessageUserProps = {
    message: NormalisedMessage
    onLoad: () => void
  }

  let { message, onLoad = noop }: MessageUserProps = $props()
</script>

<div class="message-user rounded-2xl px-5 py-3 mt-5 mb-4 md:mb-8">
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
