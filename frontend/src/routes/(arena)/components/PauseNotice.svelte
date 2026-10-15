<script lang="ts">
  import { resolve } from '$app/paths'
  import { Button, Link, Toggletip } from '$components/dsfr'
  import type { Spent } from '$lib/limits.svelte'
  import { m } from '$lib/i18n/messages'
  import LimitCard from './LimitCard.svelte'
  import { pauseTitle, resetTime } from './resetTime'
  import TimedText from './TimedText.svelte'

  let {
    pause,
    onReveal,
    failed = false,
    focusTitle = false,
    level = 3
  }: {
    /** The whole allowance, spent: for whom, and when it lifts. */
    pause: Pick<Spent, 'scope' | 'resets_at'>
    /** In a conversation: discover the models. Left out on the home page. */
    onReveal?: () => void
    /** The conversation failed, so there is nothing to vote on or reveal. */
    failed?: boolean
    /** It takes the place of the text box the person just sent from. */
    focusTitle?: boolean
    /** 2 on the home page, where the card replaces the page's question. */
    level?: 2 | 3
  } = $props()

  const reset = $derived(resetTime(pause.resets_at))
  const heading = $derived(pauseTitle(reset))
  const network = $derived(pause.scope === 'network')
</script>

<LimitCard
  id="pause-notice"
  icon="i-ri-hourglass-line"
  text={m[network ? 'arene.limits.pause.network' : 'arene.limits.pause.session']()}
  {focusTitle}
  {level}
>
  {#snippet title()}
    <TimedText text={heading} {reset} />
  {/snippet}

  {#snippet actions()}
    {#if failed}
      <Link
        button
        size="sm"
        icon="edit-line"
        href={resolve('/')}
        text={m['header.chatbot.newDiscussion']()}
        class="w-full!"
      />
    {:else if onReveal}
      <Button text={m['chatbot.revealButton']()} size="sm" class="w-full!" onclick={onReveal} />
    {:else}
      <Link
        button
        size="sm"
        href={resolve('/ranking')}
        text={m['arene.limits.pause.ranking']()}
        class="w-full!"
      />
    {/if}
    <Link
      button
      variant="secondary"
      size="sm"
      href={resolve(failed || onReveal ? '/ranking' : '/models')}
      text={m[failed || onReveal ? 'arene.limits.pause.ranking' : 'arene.limits.pause.models']()}
      class="w-full!"
    />
    <!-- TODO offer sign-in here when the scope is "session" and the person is
         anonymous, once signing in gives more room (feat/signed-in-allowance).
         Today the allowance follows the anonymous cookie, which signing in
         keeps, so the offer would not help. -->
  {/snippet}

  {#snippet footer()}
    <p class="fr-text--sm mt-4! mb-0! relative">
      <Toggletip
        id="pause-notice-why"
        label={m['arene.limits.pause.whyLabel']()}
        text={m[network ? 'arene.limits.pause.whyNetwork' : 'arene.limits.pause.why']()}
      />
    </p>
  {/snippet}
</LimitCard>
