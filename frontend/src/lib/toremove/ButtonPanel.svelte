<script lang="ts">
  import Copy from '$lib/components/Copy.svelte'
  import IconButton from '$lib/components/IconButton.svelte'
  import LikeDislike from '$lib/components/LikeDislike.svelte'
  import type { NormalisedMessage, TextMessage } from '$lib/types'
  import { Undo } from '@gradio/icons'

  export let disabled: boolean
  export let likeable: boolean
  export let show_retry: boolean
  export let show_undo: boolean
  export let show_copy_button: boolean
  export let show: boolean
  export let message: NormalisedMessage | NormalisedMessage[]
  // export let position: "right" | "left";
  export let generating: boolean

  export let handle_action: (selected: string | null) => void
  export let layout: 'bubble' | 'panel'

  function is_all_text(
    message: NormalisedMessage[] | NormalisedMessage
  ): message is TextMessage[] | TextMessage {
    return (
      (Array.isArray(message) && message.every((m) => typeof m.content === 'string')) ||
      (!Array.isArray(message) && typeof message.content === 'string')
    )
  }

  function all_text(message: TextMessage[] | TextMessage): string {
    if (Array.isArray(message)) {
      return message.map((m) => m.content).join('\n')
    }
    return message.content
  }

  $: message_text = is_all_text(message) ? all_text(message) : ''

  $: show_copy = show_copy_button && message && is_all_text(message)
</script>

<div class="button-panel">
  {#if show}
    <div class="message-buttons-left {layout} message-buttons">
      {#if show_copy}
        <Copy value={message_text} />
      {/if}
    </div>
    <div class="message-buttons-right {layout} message-buttons">
      <!-- {#if show_retry}
				<IconButton
					Icon={Retry}
					label="Retry"
					on:click={() => handle_action("retry")}
					disabled={generating || disabled}
				/>
			{/if} -->
      {#if show_undo}
        <IconButton
          label="Undo"
          Icon={Undo}
          on:click={() => handle_action('undo')}
          disabled={generating || disabled}
        />
      {/if}
      {#if likeable}
        <LikeDislike disabled={generating || disabled} {handle_action} />
      {/if}
    </div>
  {/if}
</div>

<style>
  /* .bubble :global(.icon-button-wrapper) {
		margin: 0px calc(var(--spacing-xl) * 2);
	} */
  .button-panel {
    margin-top: 2em;
    align-self: end;
  }

  .message-buttons-left {
    float: left;
    display: flex;
  }

  .message-buttons-right {
    display: flex;
    float: right;
    gap: 0.5em;
  }

  /* 
	.panel {
		display: flex;
		align-self: flex-start;
		padding: 0 var(--spacing-xl);
		z-index: var(--layer-1);
	} */
</style>
