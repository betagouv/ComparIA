<script lang="ts">
  import { resolve } from '$app/paths'
  import { Button, Icon, Link, Toggletip } from '$components/dsfr'
  import { tryGetAuthContext } from '$lib/authContext.svelte'
  import { getLimitsContext, type Spent } from '$lib/limits.svelte'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
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

  const auth = tryGetAuthContext()
  const limits = getLimitsContext()
  const times = new Intl.NumberFormat(getLocale(), { maximumFractionDigits: 1 })
  // Signing in gives the person more room, never the network: offered only
  // to someone anonymous who spent their own allowance.
  const signInFactor = $derived.by(() => {
    const factor = limits.signedInFactor
    if (network || !auth || auth.user || !factor || factor <= 1) return undefined
    return times.format(factor)
  })
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
        icon="edit-line"
        href={resolve('/')}
        text={m['header.chatbot.newDiscussion']()}
        class="w-full!"
      />
    {:else if onReveal}
      <Button text={m['chatbot.revealButton']()} class="w-full!" onclick={onReveal} />
    {:else}
      <Link
        button
        href={resolve('/ranking')}
        text={m['arene.limits.pause.ranking']()}
        class="w-full!"
      />
    {/if}
    <Link
      button
      variant="secondary"
      href={resolve(failed || onReveal ? '/ranking' : '/models')}
      text={m[failed || onReveal ? 'arene.limits.pause.ranking' : 'arene.limits.pause.models']()}
      class="w-full!"
    />
    {#if signInFactor}
      <div class="cl-pause-sign-in mt-3 pt-6">
        <p class="fr-text--sm mb-3!">
          {m['arene.limits.pause.signIn']({ times: signInFactor })}
        </p>
        <!-- DSFR opens the sign-in modal of the arena layout and gives focus
             back here on close. Signing in keeps the person on this page. -->
        <Button
          variant="tertiary"
          aria-controls="fr-modal-signin"
          data-fr-opened="false"
          class="w-full!"
        >
          <Icon icon="i-ri-login-box-line" block size="sm" class="me-1 -ms-1" />
          {m['arene.limits.pause.signInButton']()}
        </Button>
      </div>
    {/if}
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

<style>
  .cl-pause-sign-in {
    border-top: 1px solid var(--border-default-grey);
  }
</style>
