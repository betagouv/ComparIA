<script lang="ts">
  import type { ChatMessage } from '$lib/chatService.svelte'
  import Markdown from '$lib/components/markdown/MarkdownCode.svelte'
  import { onMount } from 'svelte'

  export type MessageUserProps = {
    message: ChatMessage<'user'>
  }

  let elem: HTMLDivElement
  let { message }: MessageUserProps = $props()

  onMount(() => {
    elem.scrollIntoView({ behavior: 'smooth' })
  })
</script>

<div bind:this={elem} class="message-user mb-4 mt-5 rounded-2xl px-5 py-3 md:mb-8">
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

  @media (min-width: 48em) {
    .message-user {
      width: 60%;
      margin-left: auto;
    }
  }
</style>
