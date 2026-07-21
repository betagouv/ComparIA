<script lang="ts">
  import { sanitize } from '$lib/utils/commons'
  import type { SvelteHTMLElements } from 'svelte/elements'
  import Link from './Link.svelte'

  type CheckboxLink = { label: string; href: string }

  function safeHref(href: string): string | null {
    if (href.startsWith('/') && !href.startsWith('//')) return href
    try {
      const url = new URL(href)
      return url.protocol === 'https:' ? url.toString() : null
    } catch {
      return null
    }
  }

  let {
    id,
    checked = $bindable(),
    label,
    help,
    links = [],
    linksClass,
    error,
    disabled,
    ...props
  }: {
    id: string
    checked: boolean
    label: string
    help?: string
    links?: CheckboxLink[]
    linksClass?: string
    error?: string
    disabled?: boolean
  } & SvelteHTMLElements['label'] = $props()

  const safeLinks = $derived(
    links.flatMap((link) => {
      const href = safeHref(link.href)
      return href ? [{ ...link, href }] : []
    })
  )
  const describedBy = $derived(
    error
      ? `${id}-error-messages`
      : [help ? `${id}-help` : '', safeLinks.length ? `${id}-links` : '']
          .filter(Boolean)
          .join(' ') || undefined
  )
</script>

<div class="fr-checkbox-group fr-checkbox-group--sm" class:fr-checkbox-group--error={!!error}>
  <input
    {id}
    aria-describedby={describedBy}
    aria-invalid={error ? 'true' : undefined}
    type="checkbox"
    bind:checked
    {disabled}
  />
  <label {...props} class={['fr-label text-sm! mb-4 block!', props.class]} for={id}>
    {@html sanitize(label)}
    {#if help}
      <p id="{id}-help" class="fr-message">{help}</p>
    {/if}
  </label>
  {#if safeLinks.length > 0}
    <div id="{id}-links" class="ms-8 mb-3 gap-x-3 gap-y-1 flex flex-wrap">
      {#each safeLinks as link (link.href)}
        <Link href={link.href} text={link.label} size="sm" class={linksClass} />
      {/each}
    </div>
  {/if}
  <div
    class={['fr-messages-group', { hidden: !error }]}
    id="{id}-error-messages"
    aria-live="assertive"
  >
    <p class="fr-message fr-message--error" id="{id}-error-message">
      {error}
    </p>
  </div>
</div>

<style lang="postcss">
  .fr-checkbox-group input[type='checkbox'] + label:before {
    --border-action-high-blue-france: var(--blue-france-main-525);
  }

  .fr-checkbox-group input[type='checkbox']:checked + label:before {
    --border-active-blue-france: var(--blue-france-main-525);
    background-color: var(--blue-france-main-525);
  }
</style>
