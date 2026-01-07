<script lang="ts">
  import type { ChatMessage, OnReactionFn } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { MessageBot, MessageUser } from '.'

  let {
    user,
    bots,
    index,
    generating,
    disabled,
    onReactionChange
  }: {
    user: ChatMessage<'user'>
    bots: [ChatMessage<'assistant'>, ChatMessage<'assistant'>]
    index: number
    generating: boolean
    disabled: boolean
    onReactionChange: OnReactionFn
  } = $props()

  let userMessageSize = $state(0)
</script>

<div
  class="grouped-messages px-4 not-last:mb-15 md:px-8 xl:px-16"
  style="--message-size: {userMessageSize}px;"
  {@attach scrollTo}
>
  <MessageUser bind:size={userMessageSize} message={user} />

  <div class="gap-10 md:grid-cols-2 md:gap-6 grid">
    {#each bots as botMessage, j (j)}
      <MessageBot message={botMessage} {index} {generating} {disabled} {onReactionChange} />
    {/each}
  </div>
</div>
