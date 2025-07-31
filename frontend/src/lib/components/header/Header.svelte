<script lang="ts">
  import { m } from '$lib/i18n/messages'
  import { LanguageSelector, Menubar, VoteGauge } from '.'

  let {
    hideNavigation = false,
    hideLanguageSelector = false,
    hideVoteGauge = false,
    showHelpLink = false
  }: {
    hideNavigation?: boolean
    hideLanguageSelector?: boolean
    hideVoteGauge?: boolean
    showHelpLink?: boolean
  } = $props()
</script>

{#snippet helpLink()}
  <a
    title={m['header.help.link.title']()}
    href="https://adtk8x51mbw.eu.typeform.com/to/duuGRyEX"
    target="_blank"
    rel="noopener external"
    class="fr-link fr-icon-pencil-line fr-link--icon-left shadow-none! after:content-none!"
  >
    {m['header.help.link.content']()}
  </a>
{/snippet}

<header id="main-header" class="fr-header z-1">
  <div class="fr-header__body">
    <div class="fr-container">
      <div class="fr-header__body-row fr-grid-row">
        <div class="fr-header__brand fr-enlarge-link">
          <div class="fr-header__brand-top w-auto!">
            <div class="fr-header__logo">
              <p class="fr-logo">
                République<br />Française
              </p>
            </div>
          </div>
          <div class="fr-header__service before:content-none! w-1/2 lg:w-auto">
            <a href="/" title="Accueil - compar:IA">
              <p class="fr-header__service-title">
                {m['header.title.compar']()}:{m['header.title.ia']()}
              </p>
            </a>

            <span class="fr-header__service-tagline">
              {m['header.subtitle']()}
            </span>
          </div>
          <div class="fr-header__navbar self-auto! mt-0!">
            <button
              class="fr-btn fr-btn--menu me-3!"
              data-fr-opened="false"
              aria-controls="fr-modal-menu"
              aria-haspopup="menu"
              title="Menu"
            >
              Menu
            </button>
          </div>
        </div>

        <div class="ms-auto hidden items-center gap-8 p-4 lg:flex">
          {#if !hideVoteGauge}
            <VoteGauge />
          {/if}

          {#if showHelpLink}
            {@render helpLink()}
          {/if}

          {#if !hideLanguageSelector}
            <LanguageSelector id="translate" />
          {/if}
        </div>
      </div>
    </div>
  </div>

  <dialog
    aria-labelledby="fr-modal-title-modal-menu"
    id="fr-modal-menu"
    class="fr-modal fr-header__menu lg:min-h-auto min-h-screen"
  >
    <div class="fr-container">
      <button
        class="fr-btn--close fr-btn"
        title="Fermer la fenêtre modale"
        aria-controls="fr-modal-menu">Fermer</button
      >
      <div class="fr-header__menu-links after:mt-4! relative lg:hidden">
        {#if showHelpLink}
          {@render helpLink()}
        {/if}

        {#if !hideLanguageSelector}
          <LanguageSelector id="mobile-translate" />
        {/if}
      </div>

      {#if !hideNavigation}
        <Menubar />
      {/if}
    </div>
  </dialog>
</header>

<style>
  #main-header {
    --shadow-color: rgba(0, 0, 18, 0.16);
    --raised-shadow: 0 1px 3px var(--shadow-color);
    filter: drop-shadow(0 1px 3px var(--shadow-color));
  }
</style>
