<script lang="ts">
  import { PRIVACY_POLICY_PATH } from '$lib/consent'
  import type { CookieChoice } from '$lib/cookieConsent'
  import type { PublicCookieBanner } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import { onMount, tick } from 'svelte'

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
    // Rendered in place, for the admin page, with the choice panel open.
    preview?: boolean
  } = $props()

  const id = $props.id()
  // svelte-ignore state_referenced_locally
  let panelOpen = $state(preview || !!choice)
  // svelte-ignore state_referenced_locally
  let measurement = $state(choice?.measurement ?? false)
  // svelte-ignore state_referenced_locally
  let preferences = $state(choice?.preferences ?? false)

  let titleEl = $state<HTMLHeadingElement>()
  let panelEl = $state<HTMLUListElement>()

  const kinds = $derived([
    {
      key: 'measurement',
      label: text.audience_measurement_label,
      help: text.audience_measurement_description
    },
    {
      key: 'preferences',
      label: text.remembered_settings_label,
      help: text.remembered_settings_description
    }
  ] as const)

  onMount(() => {
    // Someone who reopened the banner is sent into it. On a first visit it
    // waits right after the skip links instead of pulling focus off the page.
    if (choice && !preview) titleEl?.focus()
  })

  async function togglePanel() {
    panelOpen = !panelOpen
    if (panelOpen) {
      await tick()
      panelEl?.querySelector('input')?.focus()
    }
  }

  function closePanel() {
    panelOpen = false
    document.getElementById(`${id}-choose`)?.focus()
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key !== 'Escape') return
    if (panelOpen && panelEl?.contains(event.target as Node)) {
      event.preventDefault()
      closePanel()
    } else if (onClose) {
      event.preventDefault()
      onClose()
    }
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

  {#if panelOpen}
    <ul id="{id}-panel" bind:this={panelEl} class="kinds">
      {#each kinds as kind (kind.key)}
        <li>
          <span class="kind-text">
            <label for="{id}-{kind.key}" id="{id}-{kind.key}-label">{kind.label}</label>
            <span id="{id}-{kind.key}-help">{kind.help}</span>
          </span>
          {#if kind.key === 'measurement'}
            <input
              id="{id}-measurement"
              type="checkbox"
              class="switch"
              aria-labelledby="{id}-measurement-label"
              aria-describedby="{id}-measurement-help"
              bind:checked={measurement}
            />
          {:else}
            <input
              id="{id}-preferences"
              type="checkbox"
              class="switch"
              aria-labelledby="{id}-preferences-label"
              aria-describedby="{id}-preferences-help"
              bind:checked={preferences}
            />
          {/if}
        </li>
      {/each}
    </ul>
  {/if}

  <div class="actions">
    <button
      id="{id}-choose"
      type="button"
      class="text"
      aria-expanded={panelOpen}
      aria-controls="{id}-panel"
      onclick={togglePanel}
    >
      {m['cookieBanner.choose']()}
    </button>
    <!-- Refusing looks exactly like accepting. -->
    <button
      type="button"
      class="choice"
      onclick={() => onChoice?.({ measurement: false, preferences: false })}
    >
      {m['cookieBanner.refuseAll']()}
    </button>
    {#if panelOpen}
      <button type="button" class="choice" onclick={() => onChoice?.({ measurement, preferences })}>
        {m['cookieBanner.save']()}
      </button>
    {:else}
      <button
        type="button"
        class="choice"
        onclick={() => onChoice?.({ measurement: true, preferences: true })}
      >
        {m['cookieBanner.acceptAll']()}
      </button>
    {/if}
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
  .kinds {
    margin: 0;
    padding: 0;
    list-style: none;
    border-top: 1px solid var(--border-default-grey);
  }
  .kinds li {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.625rem 0;
    border-bottom: 1px solid var(--border-default-grey);
  }
  .kind-text {
    display: flex;
    flex: 1;
    flex-direction: column;
    min-width: 0;
    font-size: 0.75rem;
    line-height: 1.4;
    color: var(--text-mention-grey);
  }
  .kind-text label {
    font-size: 0.8125rem;
    font-weight: 600;
    color: var(--text-default-grey);
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
  button:focus-visible,
  .switch:focus-visible {
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
  .text {
    margin-right: auto;
    padding: 0.25rem 0;
    font-size: 0.8125rem;
    color: var(--text-default-grey);
    background: none;
    border: 0;
    text-decoration: underline;
    text-underline-offset: 2px;
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
  .switch {
    appearance: none;
    position: relative;
    flex: none;
    width: 2.25rem;
    height: 1.25rem;
    margin: 0;
    cursor: pointer;
    background: var(--background-contrast-grey);
    border-radius: 999px;
    box-shadow: inset 0 0 0 1px var(--border-default-grey);
    transition: background 0.15s;
  }
  .switch::before {
    content: '';
    position: absolute;
    top: 0.125rem;
    left: 0.125rem;
    width: 1rem;
    height: 1rem;
    background: #fff;
    border-radius: 50%;
    box-shadow: 0 1px 2px rgb(0 0 0 / 0.25);
    transition: transform 0.15s;
  }
  .switch:checked {
    background: var(--background-action-high-blue-france);
    box-shadow: none;
  }
  .switch:checked::before {
    transform: translateX(1rem);
  }
  @media (prefers-reduced-motion: reduce) {
    .switch,
    .switch::before {
      transition: none;
    }
  }
</style>
