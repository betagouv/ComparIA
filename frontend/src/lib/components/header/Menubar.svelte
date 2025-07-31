<script lang="ts">
  import { page } from '$app/state'
  import { m } from '$lib/i18n/messages'

  // Navigation links for both desktop and mobile menus
  const navLinks = [
    { href: '/', label: m['seo.titles.home']() },
    { href: '/modeles', label: m['seo.titles.modeles']() },
    { href: '/datasets', label: m['seo.titles.datasets']() },
    { href: '/a-propos', label: m['seo.titles.a-propos']() },
    { href: '/partenaires', label: m['seo.titles.partenaires']() },
    { href: '/faq', label: m['seo.titles.faq']() },
    { href: '/bnf', label: m['seo.titles.bnf']() }
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
