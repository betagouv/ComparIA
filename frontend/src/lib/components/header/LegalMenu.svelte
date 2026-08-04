<script lang="ts">
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import Dropdown from '$components/Dropdown.svelte'
  import { Icon } from '$components/dsfr'
  import { legalPageLinks } from '$lib/consent'
  import { m } from '$lib/i18n/messages'

  const { id, expanded = true }: { id: string; expanded?: boolean } = $props()

  // resolve() is typed for routes known at compile time, one literal per call. The
  // legal paths live in consent.ts as plain strings, so the generic signature can
  // never match.
  const resolveHref = resolve as (href: string) => string

  const links = legalPageLinks()
</script>

<nav class="legal-menu" aria-label={m['header.legal.title']()}>
  <Dropdown
    id="dropdown-{id}"
    label={m['header.legal.label']()}
    title={m['header.legal.title']()}
    buttonClass={[
      'fr-btn fr-btn--tertiary-no-outline fr-btn--sm rounded-sm! gap-2 w-full! justify-start',
      { 'lg:justify-center lg:px-0!': !expanded }
    ]}
    closeOnSelect
  >
    {#snippet buttonLabel(label: string)}
      <Icon icon="i-ri-scales-3-line" block size="sm" />
      <span class={{ 'lg:sr-only': !expanded }}>{label}</span>
      <Icon
        icon="i-ri-arrow-up-s-line"
        block
        size="xs"
        class={['legal-menu-chevron ms-auto transition-transform', { 'lg:hidden': !expanded }]}
      />
    {/snippet}

    <ul class="fr-sidemenu__list">
      {#each links as link (link.href)}
        <li class="fr-sidemenu__item">
          <a
            class="fr-sidemenu__link py-2! font-normal! font-sm!"
            href={resolveHref(link.href)}
            aria-current={page.url.pathname === link.href ? 'page' : undefined}
          >
            {link.label}
          </a>
        </li>
      {/each}
    </ul>
  </Dropdown>
</nav>

<style lang="postcss">
  .legal-menu {
    :global([aria-expanded='true'] .legal-menu-chevron) {
      transform: rotate(180deg);
    }

    :global(.fr-sidemenu__link) {
      outline-offset: -2px;

      &[aria-current]:not([aria-current='false']) {
        --text-active-blue-france: var(--blue-france-main-525);
        --border-active-blue-france: var(--blue-france-main-525);

        &::before {
          width: 4px;
          top: 0;
          bottom: 0;
        }
      }
    }
  }
</style>
