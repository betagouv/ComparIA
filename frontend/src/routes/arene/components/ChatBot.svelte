<script lang="ts">
  import { Button, Icon, Link } from '$components/dsfr'
  import Pending from '$components/Pending.svelte'
  import type { OnReactionFn } from '$lib/chatService.svelte'
  import { arena, type ChatRound } from '$lib/chatService.svelte'
  import { scrollTo } from '$lib/helpers/attachments'
  import { m } from '$lib/i18n/messages'
  import { GroupedMessages } from '.'

  let {
    disabled,
    onReactionChange,
    onRetry,
    onVote
  }: {
    disabled: boolean
    onReactionChange: OnReactionFn
    onRetry: () => void
    onVote: () => void
  } = $props()

  const rounds = $derived.by<ChatRound[]>(() => {
    const { a, b } = arena.chat
    const base = a.messages.length ? 'a' : 'b'
    const userMessages = arena.chat[base].messages.filter((m) => m.role === 'user')
    const assistantMessages = {
      a: a.messages.filter((m) => m.role === 'assistant'),
      b: b.messages.filter((m) => m.role === 'assistant')
    }
    return userMessages.map((userMessage, i) => {
      const isLast = i === userMessages.length - 1
      const msgA = assistantMessages['a'][i]
      const msgB = assistantMessages['b'][i]
      return {
        user: userMessage,
        a: isLast && msgA ? { ...msgA, generating: a.status === 'generating' } : msgA,
        b: isLast && msgB ? { ...msgB, generating: b.status === 'generating' } : msgB,
        index: i
      }
    })
  })

  const errorString = $derived(arena.chat.error)
</script>

<div
  id="chat-area"
  role="log"
  aria-label={m['chatbot.conversation']()}
  aria-live="polite"
  class="pb-7 flex grow flex-col"
>
  {#each rounds as round (round.index)}
    <GroupedMessages {round} {disabled} {onReactionChange} />
  {/each}

  {#if arena.chat.status === 'pending'}
    <Pending message={m['chatbot.loading']()} class="m-auto" {@attach scrollTo} />
  {/if}

  {#if errorString}
    <div class="fr-container">
      <div class="cg-border pe-13 lg:max-w-1/2 gap-4 bg-white p-4 pb-7 m-auto flex">
        <Icon icon="warning-fill" class="text-error" />
        <div>
          {#if errorString === 'Context too long.'}
            <h6 class="mb-2!">{m['chatbot.errors.tooLong.title']()}</h6>
            <p>
              {m['chatbot.errors.tooLong.message']()}&nbsp;{m[
                `chatbot.errors.tooLong.${rounds.length > 1 ? 'vote' : 'retry'}`
              ]()}
            </p>
          {:else}
            <h6 class="mb-2!">{m['chatbot.errors.other.title']()}</h6>
            <p>
              {m['chatbot.errors.other.message']()}<br />
              {m['chatbot.errors.other.retry']()}{#if rounds.length > 1}&nbsp;{m[
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

            {#if rounds.length > 1}
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
