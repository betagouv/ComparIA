<script lang="ts">
  import type { ChatRound, OnReactionFn } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { MessageBot, MessageUser } from '.'

  let {
    round,
    disabled,
    onReactionChange
  }: {
    round: ChatRound
    disabled: boolean
    onReactionChange: OnReactionFn
  } = $props()

  let userMessageSize = $state(0)
</script>

<div
  class="grouped-messages not-last:mb-15 px-4 md:px-8 xl:px-16"
  style="--message-size: {userMessageSize}px;"
  {@attach scrollTo}
>
  <MessageUser bind:size={userMessageSize} message={round.user} />

  <div class="gap-10 md:grid-cols-2 md:gap-6 grid">
    {#if round.a && round.b}
      <MessageBot message={round.a} index={round.index} {disabled} {onReactionChange} />
      <MessageBot message={round.b} index={round.index} {disabled} {onReactionChange} />
    {/if}
  </div>
</div>
