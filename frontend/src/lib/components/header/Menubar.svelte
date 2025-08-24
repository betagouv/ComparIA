<script lang="ts">
  import { page } from '$app/state'
  import { m } from '$lib/i18n/messages'

  // Navigation links for both desktop and mobile menus
  const navLinks = [
    { href: '/', label: m['seo.titles.home']() },
    { href: '/product', label: m['seo.titles.product']() },
    { href: '/ranking', label: m['seo.titles.ranking']() },
    { href: '/modeles', label: m['seo.titles.modeles']() },
    { href: '/datasets', label: m['seo.titles.datasets']() },
    { href: '/news', label: m['seo.titles.news']() }
  ]
</script>

<nav class="fr-nav" data-fr-js-navigation="true">
  <ul class="fr-nav__list fr-container">
    {#each navLinks as link}
      <li class="fr-nav__item" data-fr-js-navigation-item="true">
        <a
          href={link.href}
          target="_self"
          aria-controls="modal-header__menu"
          class="fr-nav__link"
          aria-current={page.url.pathname === link.href ? 'true' : undefined}
          data-fr-js-modal-button="true"
        >
          {link.label}
        </a>
      </li>
    {/each}
  </ul>
</nav>
