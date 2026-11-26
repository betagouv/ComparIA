<script lang="ts">
  import { PRIVACY_POLICY_PATH } from '$lib/consent'
  import type { CookieChoice } from '$lib/cookieConsent'
  import type { PublicCookieBanner } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  let {
    text,
    choice = null,
    onChoice,
    onClose,
    preview = false
  }: {
    text: Omit<PublicCookieBanner, 'locale'>
    // The answer already given, when the banner is reopened.
    choice?: CookieChoice | null
    onChoice?: (choice: CookieChoice) => void
    onClose?: () => void
    // Rendered in place, for the admin page.
    preview?: boolean
  } = $props()

  const id = $props.id()
  let titleEl = $state<HTMLHeadingElement>()

  onMount(() => {
    // Someone who reopened the banner is sent into it. On a first visit it
    // waits right after the skip links instead of pulling focus off the page.
    if (choice && !preview) titleEl?.focus()
  })

  function handleKeydown(event: KeyboardEvent) {
    if (event.key !== 'Escape' || !onClose) return
    event.preventDefault()
    onClose()
  }
</script>

<!-- Escape is caught for the whole banner, from whichever control has focus. -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<section
  aria-labelledby={preview ? undefined : `${id}-title`}
  onkeydown={handleKeydown}
  class={['cookie-banner', { floating: !preview }]}
>
  <div class="head">
    <h2 id="{id}-title" bind:this={titleEl} tabindex="-1">{text.title}</h2>
    {#if onClose}
      <button type="button" class="close" aria-label={m['cookieBanner.close']()} onclick={onClose}>
        <span class="fr-icon-close-line fr-icon--sm" aria-hidden="true"></span>
      </button>
    {/if}
  </div>

  <p class="description">
    {text.description}
    <!-- In the admin preview, a new tab keeps the unsaved form. -->
    <a href={PRIVACY_POLICY_PATH} {...preview ? { target: '_blank', rel: 'noopener' } : {}}>
      {m['consent.links.privacy_policy']()}
    </a>
  </p>

  {#if choice}
    <p class="current">
      {choice.measurement ? m['cookieBanner.currentYes']() : m['cookieBanner.currentNo']()}
    </p>
  {/if}

  <!-- Refusing looks exactly like accepting. -->
  <div class="actions">
    <button type="button" class="choice" onclick={() => onChoice?.({ measurement: false })}>
      {m['cookieBanner.refuse']()}
    </button>
    <button type="button" class="choice" onclick={() => onChoice?.({ measurement: true })}>
      {m['cookieBanner.accept']()}
    </button>
  </div>
</section>

<style>
  .cookie-banner {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 1rem;
    color: var(--text-default-grey);
    background: var(--background-default-grey);
    border: 1px solid var(--border-default-grey);
    border-radius: 0.75rem;
  }
  .floating {
    position: fixed;
    z-index: 1000;
    right: 0.75rem;
    bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
    left: 0.75rem;
    max-height: 70dvh;
    overflow-y: auto;
    box-shadow: 0 10px 30px rgb(0 0 0 / 0.14);
  }
  @media (min-width: 36em) {
    .floating {
      left: auto;
      right: 1rem;
      bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
      width: 24rem;
    }
  }
  .head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 0.5rem;
  }
  h2 {
    margin: 0;
    font-size: 0.9375rem;
    line-height: 1.4;
    font-weight: 700;
  }
  h2:focus {
    outline: none;
  }
  h2:focus-visible {
    outline: 2px solid var(--border-active-blue-france);
    outline-offset: 2px;
  }
  .description {
    margin: 0;
    font-size: 0.8125rem;
    line-height: 1.5;
    color: var(--text-mention-grey);
  }
  .description a {
    color: inherit;
    text-decoration: underline;
    text-underline-offset: 2px;
    background-image: none;
  }
  .current {
    margin: 0;
    font-size: 0.8125rem;
    font-weight: 600;
  }
  .actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: flex-end;
    gap: 0.5rem;
  }
  button {
    font: inherit;
    cursor: pointer;
  }
  button:focus-visible {
    outline: 2px solid var(--border-active-blue-france);
    outline-offset: 2px;
  }
  .choice {
    min-height: 2rem;
    padding: 0.25rem 0.875rem;
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text-inverted-blue-france);
    background: var(--background-action-high-blue-france);
    border: 0;
    border-radius: 0.375rem;
  }
  .choice:hover {
    background: var(--background-action-high-blue-france-hover);
  }
  .close {
    display: grid;
    place-items: center;
    width: 1.75rem;
    height: 1.75rem;
    margin: -0.25rem -0.25rem 0 0;
    color: var(--text-mention-grey);
    background: none;
    border: 0;
    border-radius: 0.375rem;
  }
  .close:hover {
    background: var(--background-default-grey-hover);
  }
</style>
