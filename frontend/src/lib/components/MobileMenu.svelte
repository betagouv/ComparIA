<script lang="ts">
  import { page } from '$app/stores'
  import { m } from '$lib/i18n/messages'
  import { setLocale } from '$lib/i18n/runtime'
  import Icon from '$lib/components/Icon.svelte'
  import Tooltip from '$lib/components/Tooltip.svelte'
  import { modeInfos, state } from '$lib/state.svelte'
  import { sanitize } from '$lib/utils/commons'

  let { children } = $props()

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

  const mode = $derived(state.mode ? modeInfos.find((mode) => mode.value === state.mode)! : null)

  // Internationalization-safe number formatting
  const NumberFormater = new Intl.NumberFormat($page.data.lang, { maximumSignificantDigits: 3 })
  const votes = $derived(
    state.votes
      ? {
          count: NumberFormater.format(state.votes.count),
          objective: NumberFormater.format(state.votes.objective),
          ratio: (100 * (state.votes.count / state.votes.objective)).toFixed() + '%'
        }
      : null
  )
</script>

<button
  class="fr-btn fr-btn--menu"
  data-fr-opened="false"
  aria-controls="fr-modal-menu"
  aria-haspopup="menu"
  aria-label={m.menu_button_title()}
></button>

<!-- Mobile Menu Modal -->
<div class="md-visible fr-header__tools fr-col-12 fr-col-lg-4 fr-p-2w hidden">
  <a
    title={m['header.help.link.title']()}
    href="https://adtk8x51mbw.eu.typeform.com/to/duuGRyEX"
    target="_blank"
    rel="noopener external"
    class="fr-link fr-icon-pencil-line fr-link--icon-left"
  >
    {m['header.help.link.content']()}
  </a>
</div>

<Modal name="mobile-menu">
  <nav
    role="navigation"
    aria-label={m.modalMenu_main_nav_label()}
    class="fr-nav fr-px-2w fr-px-md-0"
    data-fr-js-navigation="true"
  >
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
            {link.label()}
          </a>
        </li>
      {/each}
    </ul>
  </nav></Modal
>
