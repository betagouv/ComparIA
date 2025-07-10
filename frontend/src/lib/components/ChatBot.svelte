<script lang="ts">
  import { browser } from '$app/environment'
  import CopyAll from '$lib/components/CopyAll.svelte'
  import IconButton from '$lib/components/IconButton.svelte'
  import Markdown from '$lib/components/markdown/MarkdownCode.svelte'
  import type { ExtendedLikeData, NormalisedMessage } from '$lib/types'
  import { type UndoRetryData, group_messages } from '$lib/utils'
  import { ScrollDownArrow } from '@gradio/icons'
  import { onMount, tick } from 'svelte'
  import MessageBot from './MessageBot.svelte'
  import MessageUser from './MessageUser.svelte'
  import { m } from '$lib/i18n/messages'

  export let value: NormalisedMessage[] = []
  $: value

  export let disabled = false
  export let pending_message = false
  export let generating = false
  export let show_copy_all_button = false
  export let autoscroll = true
  export let layout: 'bubble' | 'panel' = 'bubble'
  export let placeholder: string | null = null
  export let onLike: (data: ExtendedLikeData) => void
  export let onRetry: (data: UndoRetryData) => void

  let div: HTMLDivElement

  let show_scroll_button = false

  function is_at_bottom(): boolean {
    return div && div.offsetHeight + div.scrollTop > div.scrollHeight - 100
  }

  function scroll_to_bottom(): void {
    if (!div) return
    div.scrollTo(0, div.scrollHeight)
    show_scroll_button = false
  }

  let scroll_after_component_load = false

  async function scroll_on_value_update(): Promise<void> {
    if (!autoscroll) return

    if (is_at_bottom()) {
      // Child components may be loaded asynchronously,
      // so trigger the scroll again after they load.
      scroll_after_component_load = true

      await tick() // Wait for the DOM to update so that the scrollHeight is correct
      scroll_to_bottom()
    } else {
      show_scroll_button = true
    }
  }
  onMount(() => {
    scroll_on_value_update()
  })
  $: if (value || pending_message) {
    scroll_on_value_update()
  }

  onMount(() => {
    function handle_scroll(): void {
      if (is_at_bottom()) {
        show_scroll_button = false
      } else {
        scroll_after_component_load = false
      }
    }

    div?.addEventListener('scroll', handle_scroll)
    return () => {
      div?.removeEventListener('scroll', handle_scroll)
    }
  })

  export let hasError: boolean = false
  export let errorString: string | null = null
  $: {
    errorString = null

    for (const messages of groupedMessages) {
      for (const message of messages.bots) {
        if (message?.error) {
          errorString = message.error
          break
        }
      }
      if (errorString !== null) {
        break
      }
    }

    hasError = errorString !== null
  }

  $: groupedMessages = value && group_messages(value)

  function handle_retry_last(): void {
    // svelte custom_components/customchatbot/frontend/shared/ChatBot.svelte (237-238)
    const lastGroup = groupedMessages[groupedMessages.length - 1]?.bots
    const lastMessage = lastGroup && lastGroup.length > 0 ? lastGroup[lastGroup.length - 1] : null
    if (!lastMessage || !lastMessage.error) return
    console.log('RETRYING')

    onRetry({
      index: lastMessage.index,
      value: lastMessage.error
      // lastMessage.metadata?.error ||
      //  ||
      // lastMessage.content,
      // value: msg.content,
      // error: msg.metadata?.error || msg.error
    })
  }

  const onReaction = (kind: 'like' | 'comment', message: NormalisedMessage) => {
    value[message.index] = message

    if (kind === 'like') {
      onLike({
        index: message.index,
        value: message.content,
        liked: message.liked ? true : message.disliked ? false : undefined,
        prefs: message.prefs
      })
    } else {
      onLike({
        index: message.index,
        value: '',
        comment: message.comment
      })
    }
  }
</script>

{#if value !== null && value.length > 0}
  <div>
    {#if show_copy_all_button}
      <CopyAll {value} />
    {/if}
  </div>
{/if}

<div
  class={layout === 'bubble' ? 'bubble-wrap' : 'panel-wrap'}
  bind:this={div}
  role="log"
  aria-label={m['chatbot.conversation']()}
  aria-live="polite"
>
  {#if value !== null && value.length > 0 && groupedMessages !== null}
    {#each groupedMessages as { user: userMessage, bots }, i}
      <div class="mb-15 px-4 md:px-8 xl:px-16">
        <MessageUser message={userMessage} onLoad={browser ? scroll : () => {}} />

        <div class="grid gap-10 md:grid-cols-2 md:gap-6">
          {#each bots as botMessage, j}
            <MessageBot
              message={botMessage}
              {generating}
              {disabled}
              onLoad={browser ? scroll : () => {}}
              {onReaction}
            />
          {/each}
        </div>
      </div>
    {/each}
  {:else}
    <!-- TODO: remove this placeholder, if it appears it should be an error instead -->
    <div class="placeholder-content">
      {#if placeholder !== null}
        <div class="placeholder">
          <Markdown message={placeholder} />
        </div>
      {/if}
    </div>
  {/if}

  {#if hasError}
    <div class="fr-py-4w fr-mb-4w error rounded-tile fr-container">
      {#if errorString == 'Context too long.'}
        <h5>
          <span class="fr-icon-warning-fill" aria-hidden="true"></span>
          {m['chatbot.errors.tooLong.title']()}
        </h5>
        <p>
          {m['chatbot.errors.tooLong.message']()}&nbsp;{m[
            `chatbot.errors.tooLong.${groupedMessages.length > 1 ? 'vote' : 'retry'}`
          ]()}
        </p>
        <p class="text-center">
          <!-- TODO: icone Recommencer -->
          <a class="btn purple-btn" href="../arene/?cgu_acceptees" target="_blank"
            >{m['words.restart']()}</a
          >
          <!-- TODO: Bouton "donner son avis" -->
        </p>
      {:else}
        <h3>
          <span class="fr-icon-warning-fill" aria-hidden="true"></span>
          {m['chatbot.errors.other.title']()}
        </h3>
        <p>
          {m['chatbot.errors.other.message']()}<br />
          {m['chatbot.errors.other.retry']()}{#if groupedMessages.length > 1}&nbsp;{m[
              'chatbot.errors.other.vote'
            ]()}{/if}.
          <span class="hidden">{errorString}</span>
        </p>
        <p class="text-center">
          <button
            class="fr-btn purple-btn"
            on:click={() => handle_retry_last()}
            disabled={generating || disabled}>{m['words.retry']}</button
          >
        </p>
      {/if}
    </div>
  {/if}
</div>

{#if show_scroll_button}
  <div class="scroll-down-button-container">
    <IconButton
      Icon={ScrollDownArrow}
      label="Scroll down"
      size="large"
      on:click={scroll_to_bottom}
    />
  </div>
{/if}

<style>
  .placeholder-content {
    display: flex;
    flex-direction: column;
    height: 100%;
  }

  .placeholder {
    align-items: center;
    display: flex;
    justify-content: center;
    height: 100%;
    flex-grow: 1;
  }

  .panel-wrap {
    width: 100%;
    /* overflow-y: auto; */
    background-color: #fcfcfd;
  }

  .bubble-wrap {
    width: 100%;
    /* overflow-y: auto; */
    height: 100%;
    padding-top: var(--spacing-xxl);
  }

  @media (prefers-color-scheme: dark) {
    .bubble-wrap {
      background: var(--background-fill-secondary);
    }
  }

  .scroll-down-button-container {
    position: absolute;
    bottom: 10px;
    left: 50%;
    transform: translateX(-50%);
    z-index: var(--layer-top);
  }
  .scroll-down-button-container :global(button) {
    border-radius: 50%;
    box-shadow: var(--shadow-drop);
    transition:
      box-shadow 0.2s ease-in-out,
      transform 0.2s ease-in-out;
  }
  .scroll-down-button-container :global(button:hover) {
    box-shadow:
      var(--shadow-drop),
      0 2px 2px rgba(0, 0, 0, 0.05);
    transform: translateY(-2px);
  }

  .fr-icon-warning-fill::before,
  .fr-icon-warning-fill::after {
    /* --warning-425-625 */
    color: #b34000;
    background-color: #b34000;
    -webkit-mask-image: url('../assets/dsfr/icons/system/fr--warning-fill.svg');
    mask-image: url('../assets/dsfr/icons/system/fr--warning-fill.svg');
  }
</style>
