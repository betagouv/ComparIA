<script lang="ts">
  import { Icon, Link } from '$components/dsfr'
  import { legalPageLinks } from '$lib/consent'
  import { m } from '$lib/i18n/messages'

  const { id, expanded = true }: { id: string; expanded?: boolean } = $props()

  const links = legalPageLinks()

  let open = $state(false)
  let root = $state<HTMLDivElement>()

  function closeOnOutsideClick(event: MouseEvent) {
    if (open && root && !root.contains(event.target as Node)) open = false
  }

  function closeOnEscape(event: KeyboardEvent) {
    if (!open || event.key !== 'Escape') return
    open = false
    document.getElementById(`${id}-trigger`)?.focus()
  }
</script>

<svelte:window onclick={closeOnOutsideClick} onkeydown={closeOnEscape} />

<div bind:this={root} class="relative">
  <button
    id="{id}-trigger"
    type="button"
    aria-expanded={open}
    aria-controls={id}
    onclick={() => (open = !open)}
    class={[
      'text-grey! px-0 py-2 rounded gap-1 flex cursor-pointer items-center text-[13px]! whitespace-nowrap hover:bg-[--background-contrast-grey]',
      { 'lg:h-6 lg:w-6 lg:justify-center lg:py-0': !expanded }
    ]}
  >
    <Icon icon="i-ri-scales-3-line" block size="sm" />
    <span class={{ 'lg:sr-only': !expanded }}>{m['header.legal.label']()}</span>
    <Icon
      icon="i-ri-arrow-up-s-line"
      block
      size="xs"
      class={['transition-transform', { 'rotate-180': open, 'lg:hidden': !expanded }]}
    />
  </button>

  <nav
    {id}
    aria-label={m['header.legal.title']()}
    hidden={!open}
    class="lg:absolute lg:bottom-full lg:left-0 lg:w-[290px] lg:mb-2 p-3 bg-white rounded shadow-lg z-100 border border-[--border-default-grey]"
  >
    <p class="fr-text--sm font-bold mb-2!">{m['header.legal.title']()}</p>
    <ul class="fr-raw-list gap-2 flex flex-col items-start">
      {#each links as link (link.href)}
        <li>
          <Link href={link.href} text={link.label} size="sm" onclick={() => (open = false)} />
        </li>
      {/each}
    </ul>
  </nav>
</div>
