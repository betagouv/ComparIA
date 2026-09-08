<script module lang="ts">
  import { page } from '$app/state'
  import type { ResolvedPathname } from '$app/types'

  export type TabNavLinkProps = {
    href: ResolvedPathname
    label: string
    icon?: string
  } & SvelteHTMLElements['a']
</script>

<script lang="ts">
  import type { SvelteHTMLElements } from 'svelte/elements'
  import { Icon } from '.'

  let {
    links,
    ...props
  }: {
    links: TabNavLinkProps[]
  } & SvelteHTMLElements['nav'] = $props()
</script>

<nav {...props} class={['fr-nav', props.class]}>
  <ul class="fr-nav__list">
    {#each links as link (link.href)}
      <li class="fr-nav__item m-0!">
        <a
          href={link.href}
          class="fr-nav__link cl-nav-link py-2! min-h-unset! relative"
          aria-current={page.url.pathname.includes(link.href) ? 'true' : undefined}
        >
          <span>
            {#if link.icon}<Icon icon={link.icon} size="sm" class="me-2" />{/if}
            {link.label}
          </span>
        </a>
      </li>
    {/each}
  </ul>
</nav>

<style lang="postcss">
  .cl-nav-link {
    --border-color: var(--border-default-grey);

    &::before {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      width: 100%;
      height: 2px;
      background-color: var(--border-color) !important;
    }

    &:hover {
      --border-color: var(--border-contrast-grey);
    }

    &[aria-current]:not([aria-current='false']) {
      --text-active-blue-france: var(--blue-france-main-525);
      --border-color: var(--blue-france-main-525);
    }
  }
</style>
