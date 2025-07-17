<script lang="ts">
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
  //   const navLinks = [
  //     { href: '/', label: m.nav_home },
  //     { href: '/modeles', label: m.nav_models },
  //     { href: '/datasets', label: m.nav_datasets },
  //     { href: '/a-propos', label: m.nav_about },
  //     { href: '/partenaires', label: m.nav_partners },
  //     { href: '/faq', label: m.nav_faq },
  //     { href: '/bnf', label: m.nav_conferences }
  //   ]

  import { page } from '$app/stores'
</script>

<nav class="fr-nav fr-px-2w fr-px-md-0" data-fr-js-navigation="true">
  <ul class="fr-nav__list fr-container">
    {#each navLinks as link}
      <li class="fr-nav__item" data-fr-js-navigation-item="true">
        <a
          href={link.href}
          target="_self"
          aria-controls="modal-header__menu"
          class="fr-nav__link"
          aria-current={$page.url.pathname === link.href ? 'true' : undefined}
          data-fr-js-modal-button="true"
        >
          {link.label}
        </a>
      </li>
    {/each}
  </ul>
</nav>
