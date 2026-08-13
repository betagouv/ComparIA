<script lang="ts">
  import { page } from '$app/state'
  import { m } from '$lib/i18n/messages'

  // Navigation links for both desktop and mobile menus
  const navLinks = [{ href: '/', label: m['seo.titles.home']() }]

  function isCurrentPage(path: string, href: string) {
    return path === href
  }
</script>

<nav class="fr-nav" data-fr-js-navigation="true">
  <ul class="fr-nav__list fr-container">
    {#each navLinks as link (link.href)}
      <li class="fr-nav__item" data-fr-js-navigation-item="true">
        <a
          href={link.href}
          target="_self"
          aria-controls="modal-header__menu"
          class="fr-nav__link"
          aria-current={isCurrentPage(page.url.pathname, link.href) ? 'true' : undefined}
          data-fr-js-modal-button="true"
        >
          {link.label}
        </a>
      </li>
    {/each}
  </ul>
</nav>
