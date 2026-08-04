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
      'legal-menu-btn fr-btn fr-btn--tertiary-no-outline rounded-sm! gap-2 justify-start',
      { 'lg:w-full lg:justify-center lg:px-0!': !expanded }
    ]}
    closeOnSelect
  >
    {#snippet buttonLabel(label: string)}
      <Icon icon="i-ri-scales-3-line" block size="xs" />
      <span class={{ 'lg:sr-only': !expanded }}>{label}</span>
      <Icon
        icon="i-ri-arrow-down-s-line"
        block
        size="xs"
        class={['legal-menu-chevron ms-auto transition-transform', { 'lg:hidden': !expanded }]}
      />
    {/snippet}

    <ul class="fr-sidemenu__list">
      {#each links as link (link.href)}
        <li class="fr-sidemenu__item">
          <a
            class="fr-sidemenu__link py-2! text-sm! font-normal!"
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
    :global(.legal-menu-btn) {
      /* Same metrics and states as the DSFR translate button */
      min-height: 2.5rem;
      padding: 0.5rem 1rem;
      font-size: 1rem;
      line-height: 1.5rem;
      font-weight: 500;
      color: var(--text-default-grey);

      /* On desktop the translate button compacts, so does this one */
      @media (min-width: 62em) {
        min-height: auto;
        padding: 0.25rem 0.75rem;
        font-size: 0.875rem;
      }

      &[aria-expanded='true'] {
        color: var(--text-active-blue-france);
        background-color: var(--background-open-blue-france);
        --idle: transparent;
        --hover: var(--background-open-blue-france-hover);
        --active: var(--background-open-blue-france-active);

        &:hover {
          background-color: var(--hover-tint);
        }

        &:active {
          background-color: var(--active-tint);
        }
      }
    }

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
