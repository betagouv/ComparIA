<script lang="ts">
  import { Icon, Tooltip } from '$components/dsfr'
  import type { ChatRound, Mode, OnReactionFn } from '$lib/chatService.svelte'
  import { modeInfos } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { onMount } from 'svelte'
  import { MessageBot, MessageUser } from '.'

  let {
    round,
    disabled,
    mode: arenaMode,
    onReactionChange
  }: {
    round: ChatRound
    disabled: boolean
    mode: Mode
    onReactionChange: OnReactionFn
  } = $props()

  let userBlockElem = $state<HTMLDivElement>()
  let userMessageSize = $state(0)

  const mode = $derived(modeInfos.find((mode) => mode.value === arenaMode)!)

  onMount(() => {
    userMessageSize = userBlockElem!.offsetHeight
  })
</script>

<div
  class="grouped-messages not-last:mb-15 px-4 md:px-8 xl:px-16"
  style="--message-size: {userMessageSize}px;"
  {@attach scrollTo}
>
  <div class="mb-4 mt-5 md:mb-8 md:flex" bind:this={userBlockElem}>
    {#if round.index === 0}
      <div
        class="cg-border md:me-3 rounded-lg! bg-white py-1 text-sm mb-3 md:mb-0 px-10 md:py-3 min-w-fit self-start border-dashed! text-center"
      >
        <Icon icon={mode!.icon} size="sm" class="text-primary" />
        <strong>{mode!.title}</strong>
        <Tooltip id="mode-desc" text={mode!.description} size="xs" />
      </div>
    {/if}

    <MessageUser message={round.user} />
  </div>

  <div class="gap-10 md:grid-cols-2 md:gap-6 grid">
    {#if round.a && round.b && round.showMessages}
      <MessageBot message={round.a} bot="a" index={round.index} {disabled} {onReactionChange} />
      <MessageBot message={round.b} bot="b" index={round.index} {disabled} {onReactionChange} />
    {/if}
  </div>
</div>
