<script lang="ts">
  import { Button, Icon, Link } from '$components/dsfr'
  import Pending from '$components/Pending.svelte'
  import type { GroupedChatMessages, OnReactionFn } from '$lib/chatService.svelte'
  import { arena } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { m } from '$lib/i18n/messages'
  import { GroupedMessages } from '.'

  let {
    pending,
    generating,
    disabled,
    onReactionChange,
    onRetry,
    onVote
  }: {
    pending: boolean
    generating: boolean
    disabled: boolean
    onReactionChange: OnReactionFn
    onRetry: () => void
    onVote: () => void
  } = $props()

  const groupedMessages = $derived.by(() => {
    const questionCount = Math.ceil(arena.chat.messages.length / 3)
    const messages = arena.chat.messages.map((message, index) => ({
      ...message,
      index,
      isLast: index >= (questionCount - 1) * 3,
      // FIXME still needed ?
      content: message.content.replace('src="/file', `src="${arena.chat.root}file`)
    }))
    // Group messages by exchange (1 user question, 2 bots answers)
    return Array.from(new Array(questionCount), (_, i) => messages.slice(i * 3, i * 3 + 3)).map(
      ([user, ...bots]) => ({ user, bots }) as GroupedChatMessages
    )
  })

  const errorString = $derived(arena.chat.messages.find((message) => message.error !== null)?.error)
</script>

<div
  id="chat-area"
  role="log"
  aria-label={m['chatbot.conversation']()}
  aria-live="polite"
  class="pb-7 flex grow flex-col"
>
  {#each groupedMessages as { user, bots }, i (i)}
    <GroupedMessages {user} {bots} index={i + 1} {generating} {disabled} {onReactionChange} />
  {/each}

  {#if pending}
    <Pending message={m['chatbot.loading']()} class="m-auto" {@attach scrollTo} />
  {/if}

  {#if errorString}
    <div class="fr-container">
      <div class="cg-border gap-4 bg-white p-4 pe-13 pb-7 lg:max-w-1/2 m-auto flex">
        <Icon icon="warning-fill" class="text-error" />
        <div>
          {#if errorString === 'Context too long.'}
            <h6 class="mb-2!">{m['chatbot.errors.tooLong.title']()}</h6>
            <p>
              {m['chatbot.errors.tooLong.message']()}&nbsp;{m[
                `chatbot.errors.tooLong.${groupedMessages.length > 1 ? 'vote' : 'retry'}`
              ]()}
            </p>
          {:else}
            <h6 class="mb-2!">{m['chatbot.errors.other.title']()}</h6>
            <p>
              {m['chatbot.errors.other.message']()}<br />
              {m['chatbot.errors.other.retry']()}{#if groupedMessages.length > 1}&nbsp;{m[
                  'chatbot.errors.other.vote'
                ]()}{/if}.
              <span class="hidden">{errorString}</span>
            </p>
          {/if}

          <div class="gap-5 md:grid-cols-2 grid">
            {#if errorString === 'Context too long.'}
              <Link
                button
                icon="refresh-line"
                iconPos="right"
                variant="secondary"
                href="../arene/?cgu_acceptees"
                text={m['words.restart']()}
                class="w-full!"
              />
            {:else}
              <Button
                icon="checkbox-fill"
                iconPos="right"
                text={m['words.retry']()}
                onclick={() => onRetry()}
                class="w-full!"
              />
            {/if}

            {#if groupedMessages.length > 1}
              <Button
                icon="checkbox-fill"
                iconPos="right"
                text={m['actions.vote']()}
                onclick={() => onVote()}
                class="w-full!"
              />
            {/if}
          </div>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  :global(#chat-area:has(+ #send-area) .grouped-messages:last-of-type) {
    min-height: calc(100vh - var(--second-header-size) - var(--footer-size));
    scroll-margin-top: calc(var(--second-header-size));
  }
</style>
