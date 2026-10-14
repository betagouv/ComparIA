<script lang="ts">
  import { resolve } from '$app/paths'
  import { Button, Icon, Link, Toggletip } from '$components/dsfr'
  import type { PauseRefusal } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'
  import { pauseTitle, resetTime } from './resetTime'
  import TimedText from './TimedText.svelte'

  let {
    refusal,
    onReveal,
    failed = false,
    focusTitle = false
  }: {
    refusal: PauseRefusal
    /** In a conversation: discover the models. Left out on the home page. */
    onReveal?: () => void
    /** The conversation failed, so there is nothing to vote on or reveal. */
    failed?: boolean
    /** It takes the place of the text box the person just sent from. */
    focusTitle?: boolean
  } = $props()

  const reset = $derived(resetTime(refusal.limit.resets_at))
  const title = $derived(pauseTitle(reset))
  const network = $derived(refusal.limit.scope === 'network')

  let titleEl = $state<HTMLHeadingElement>()

  // After a refused send the card takes the place of the text box the person
  // sent from, so focus would fall to the page. Shown before anyone sends, it
  // is part of the page and leaves focus alone.
  onMount(() => {
    if (!focusTitle || !titleEl) return
    titleEl.tabIndex = -1
    titleEl.focus()
  })
</script>

<div id="pause-notice" class="cl-pause-card cg-border px-6 py-8 mx-auto w-full text-center">
  <span class="cl-pause-card__icon mb-4 mx-auto flex items-center justify-center">
    <Icon icon="i-ri-hourglass-line" size="md" block />
  </span>
  <h3 bind:this={titleEl} class="fr-h6 mb-2!"><TimedText text={title} {reset} /></h3>
  <p class="fr-text--sm mb-6!">
    {m[network ? 'arene.limits.pause.network' : 'arene.limits.pause.session']()}
  </p>

  <div class="gap-3 flex flex-col">
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
  </div>

  <p class="fr-text--sm mt-4 mb-0! relative">
    <Toggletip
      id="pause-notice-why"
      label={m['arene.limits.pause.whyLabel']()}
      text={m[network ? 'arene.limits.pause.whyNetwork' : 'arene.limits.pause.why']()}
    />
  </p>
</div>

<style>
  .cl-pause-card {
    max-width: 26rem;
    background-color: var(--background-default-grey);
  }

  .cl-pause-card__icon {
    width: 2.75rem;
    height: 2.75rem;
    border-radius: 50%;
    background-color: var(--background-action-low-blue-france);
    color: var(--text-action-high-blue-france);
  }
</style>
