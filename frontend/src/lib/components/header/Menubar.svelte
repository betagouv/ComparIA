<script lang="ts">
  import { page } from '$app/state'

  // Navigation links for both desktop and mobile menus
  const navLinks = [
    { href: '/', label: 'Accueil' },
    { href: '/modeles', label: 'Modèles' },
    { href: '/datasets', label: 'Jeux de données' },
    { href: '/a-propos', label: 'A propos' },
    { href: '/partenaires', label: 'Partenaires' },
    { href: '/faq', label: 'FAQ' },
    { href: '/bnf', label: 'Conférences' }
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
