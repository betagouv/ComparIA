<script lang="ts">
  import { Button, Checkbox, Link } from '$components/dsfr'
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
  aria-labelledby="{id}-title"
  onkeydown={handleKeydown}
  class={[
    'p-4 md:p-6 bg-white overflow-y-auto',
    preview
      ? 'cg-border'
      : 'inset-x-0 bottom-0 shadow-lg fixed z-[1000] max-h-[60dvh] border-t-1 border-solid border-[--border-default-grey]'
  ]}
>
  <div class="max-w-4xl gap-4 mx-auto flex flex-col">
    <div class="gap-4 flex items-start justify-between">
      <h2 id="{id}-title" bind:this={titleEl} tabindex="-1" class="fr-h5 mb-0!">{text.title}</h2>
      {#if onClose}
        <Button
          variant="tertiary-no-outline"
          size="sm"
          icon="close-line"
          iconPos="right"
          text={m['cookieBanner.close']()}
          onclick={onClose}
        />
      {/if}
    </div>

    <p class="fr-text--sm mb-0!">
      {text.description}
      <Link href={PRIVACY_POLICY_PATH} text={m['consent.links.privacy_policy']()} size="sm" />
    </p>

    <div class="gap-3 flex flex-wrap">
      <Button
        text={m['cookieBanner.acceptAll']()}
        onclick={() => onChoice?.({ measurement: true, preferences: true })}
      />
      <Button
        text={m['cookieBanner.refuseAll']()}
        onclick={() => onChoice?.({ measurement: false, preferences: false })}
      />
      <Button
        id="{id}-choose"
        text={m['cookieBanner.choose']()}
        aria-expanded={panelOpen}
        aria-controls="{id}-panel"
        onclick={togglePanel}
      />
    </div>

    {#if panelOpen}
      <ul id="{id}-panel" bind:this={panelEl} class="ps-0! mb-0! list-none">
        <li>
          <Checkbox
            id="{id}-measurement"
            label={text.audience_measurement_label}
            help={text.audience_measurement_description}
            bind:checked={measurement}
          />
        </li>
        <li>
          <Checkbox
            id="{id}-preferences"
            label={text.remembered_settings_label}
            help={text.remembered_settings_description}
            bind:checked={preferences}
          />
        </li>
      </ul>
      <div>
        <Button
          variant="secondary"
          text={m['cookieBanner.save']()}
          onclick={() => onChoice?.({ measurement, preferences })}
        />
      </div>
    {/if}
  </div>
</section>
