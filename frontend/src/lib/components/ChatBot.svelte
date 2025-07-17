<script lang="ts">
  import type { GroupedChatMessages, OnReactionFn } from '$lib/chatService.svelte'
  import { chatbot } from '$lib/chatService.svelte'
  import Icon from '$lib/components/Icon.svelte'
  import MessageBot from '$lib/components/MessageBot.svelte'
  import MessageUser from '$lib/components/MessageUser.svelte'
  import Pending from '$lib/components/Pending.svelte'
  import { m } from '$lib/i18n/messages'

  let {
    pending,
    generating,
    disabled,
    layout = 'bubble',
    onReactionChange,
    onRetry
  }: {
    pending: boolean
    generating: boolean
    disabled: boolean
    layout: 'bubble' | 'panel'
    onReactionChange: OnReactionFn
    onRetry: () => void
  } = $props()

  const groupedMessages = $derived.by(() => {
    const questionCount = Math.ceil(chatbot.messages.length / 3)
    const messages = chatbot.messages.map((message, index) => ({
      ...message,
      index,
      isLast: index >= (questionCount - 1) * 3,
      // FIXME still needed ?
      content: message.content.replace('src="/file', `src="${chatbot}file`)
    }))
    // Group messages by exchange (1 user question, 2 bots answers)
    return Array.from(new Array(questionCount), (_, i) => messages.slice(i * 3, i * 3 + 3)).map(
      ([user, ...bots]) => ({ user, bots }) as GroupedChatMessages
    )
  })

  const errorString = $derived(chatbot.messages.find((message) => message.error !== null)?.error)
</script>

<!-- FIXME still needed? -->
<!-- {#if value !== null && value.length > 0}
  <div>
    {#if show_copy_all_button}
      <CopyAll {value} />
    {/if}
  </div>
{/if} -->

<div
  class={(layout === 'bubble' ? 'bubble-wrap' : 'panel-wrap') + ' min-h-full'}
  role="log"
  aria-label={m['chatbot.conversation']()}
  aria-live="polite"
>
  {#if !pending}
    {#each groupedMessages as { user, bots }, i}
      <div class="grouped-messages not-last:mb-15 px-4 md:px-8 xl:px-16">
        <MessageUser message={user} />

        <div class="grid gap-10 md:grid-cols-2 md:gap-6">
          {#each bots as botMessage, j}
            <MessageBot message={botMessage} {generating} {disabled} {onReactionChange} />
          {/each}
        </div>
      </div>
    {/each}
  {:else}
    <div class="my-6"><Pending /></div>
  {/if}

  {#if errorString}
    <div class="fr-py-4w fr-mb-4w error rounded-tile fr-container">
      {#if errorString == 'Context too long.'}
        <h5>
          <Icon icon="warning-fill" class="text-error" />
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
          <Icon icon="warning-fill" class="text-error" />
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
            onclick={() => onRetry()}
            disabled={generating || disabled}>{m['words.retry']()}</button
          >
        </p>
      {/if}
    </div>
  {/if}
</div>

<!-- FIXME still needed? -->
<!-- {#if show_scroll_button}
  <div class="scroll-down-button-container">
    <IconButton
      Icon={ScrollDownArrow}
      label="Scroll down"
      size="large"
      on:click={scroll_to_bottom}
    />
  </div>
{/if} -->

<style>
  .grouped-messages:last-of-type {
    min-height: calc(100vh - var(--second-header-size) - var(--footer-size));
  }
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
</style>
