<script lang="ts">
  import { resolve } from '$app/paths'
  import { Alert, Button, Link } from '$components/dsfr'
  import type { PauseRefusal } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { TIME_SLOT, resetTime } from './resetTime'
  import TimedText from './TimedText.svelte'

  let {
    refusal,
    onReveal,
    failed = false
  }: {
    refusal: PauseRefusal
    /** In a conversation: discover the models. Left out on the home page. */
    onReveal?: () => void
    /** The conversation failed, so there is nothing to vote on or reveal. */
    failed?: boolean
  } = $props()

  const reset = $derived(resetTime(refusal.limit.resets_at))
  const title = $derived(
    !reset.clock
      ? m['arene.limits.pause.titleSoon']()
      : m[reset.clock.tomorrow ? 'arene.limits.pause.titleTomorrow' : 'arene.limits.pause.title']({
          time: TIME_SLOT
        })
  )
  const network = $derived(refusal.limit.scope === 'network')
</script>

{#snippet titleWithTime()}
  <TimedText text={title} {reset} />
{/snippet}

<!-- The notice takes the place of the text box the person just sent from, so
     without focusTitle focus would fall to the page. -->
<Alert id="pause-notice" title={titleWithTime} focusTitle class="w-full">
  <p>
    <TimedText
      text={m[network ? 'arene.limits.pause.network' : 'arene.limits.pause.session']({
        at: reset.at
      })}
      {reset}
    />
  </p>
  {#if !network && !failed}
    <p>{m['arene.limits.pause.meanwhile']()}</p>
  {/if}

  <div class="mt-4 gap-3 md:flex-row flex flex-col">
    {#if failed}
      <Link
        button
        size="sm"
        icon="edit-line"
        href={resolve('/')}
        text={m['header.chatbot.newDiscussion']()}
        class="md:w-fit! w-full!"
      />
    {:else if onReveal}
      <Button
        text={m['arene.limits.pause.reveal']()}
        size="sm"
        class="md:w-fit! w-full!"
        onclick={onReveal}
      />
    {:else}
      <Link
        button
        size="sm"
        href={resolve('/ranking')}
        text={m['arene.limits.pause.ranking']()}
        class="md:w-fit! w-full!"
      />
    {/if}
    <!-- TODO offer sign-in here when the scope is "session" and the person is
         anonymous, once signing in gives more room (feat/signed-in-allowance).
         Today the allowance follows the anonymous cookie, which signing in
         keeps, so the offer would not help. -->
  </div>
</Alert>
