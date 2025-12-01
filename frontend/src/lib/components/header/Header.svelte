<script lang="ts">
  import { page } from '$app/state'
  import { Button, Link } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getLocale } from '$lib/i18n/runtime'
  import { LanguageSelector, Menubar, VoteGauge } from '.'

  let {
    hideNavigation = false,
    hideLanguageSelector = false,
    hideVoteGauge = false,
    hideDiscussBtn = false,
    showHelpLink = false,
    small
  }: {
    hideNavigation?: boolean
    hideLanguageSelector?: boolean
    hideVoteGauge?: boolean
    hideDiscussBtn?: boolean
    showHelpLink?: boolean
    small?: boolean
  } = $props()

  const locale = getLocale()
</script>

{#snippet helpLink()}
  <Link
    href="https://adtk8x51mbw.eu.typeform.com/to/duuGRyEX"
    text={m['header.help.link.content']()}
    title={m['header.help.link.title']()}
    icon="pencil-line"
    button
    variant="tertiary-no-outline"
    size="sm"
    native
    hideExternalIcon
  />
{/snippet}

<header id="main-header" class="fr-header overflow-hidden lg:overflow-visible">
  <div class="fr-header__body">
    <div class="fr-container">
      <div class={['fr-header__body-row', { 'lg:py-1!': small }]}>
        <div
          class={['fr-header__brand fr-enlarge-link', { 'lg:-translate-x-1/8 lg:scale-75': small }]}
        >
          <div class="fr-header__brand-top w-auto!">
            <div class="fr-header__logo">
              {#if locale === 'fr' || locale === 'en'}
                <p class="fr-logo">
                  République<br />Française
                </p>
              {:else if locale === 'da'}
                <img
                  src="/orgs/countries/da-light.png"
                  alt={m['header.logoAlt']()}
                  class="max-h-[55px] dark:hidden"
                />
                <img
                  src="/orgs/countries/da-dark.png"
                  alt={m['header.logoAlt']()}
                  class="hidden max-h-[55px] dark:block"
                />
              {:else}
                <img
                  src={`/orgs/countries/${locale}.png`}
                  alt={m['header.logoAlt']()}
                  class="max-h-[68px]"
                />
              {/if}
            </div>
          </div>
          <div
            class="fr-header__service before:content-none! md:px-3! mx-1! sm:mx-3! flex w-1/2 grow items-center sm:w-auto"
          >
            <img
              src="/orgs/comparia.png"
              aria-hidden="true"
              alt=""
              width="46"
              class="me-4 hidden h-max sm:block"
            />
            <div>
              <p class="fr-header__service-title mb-0! leading-normal!">
                <a
                  href="/"
                  target={page.url.pathname.includes('arene') ? '_blank' : undefined}
                  title={m['header.homeTitle']()}
                >
                  {m['header.title']()}
                </a>
              </p>

              <p
                class="fr-header__service-tagline text-dark-grey text-[10px]! md:text-[14px]! leading-normal! mb-0!"
              >
                {m['header.subtitle']()}
              </p>
            </div>
          </div>
          <div class="fr-header__navbar self-auto! mt-0!">
            <button
              class="fr-btn fr-btn--menu me-3! -ms-1!"
              data-fr-opened="false"
              aria-controls="fr-modal-menu"
              aria-haspopup="menu"
              title={m['header.menu']()}
            >
              {m['header.menu']()}
            </button>
          </div>
        </div>

        <div class="ms-auto hidden items-center gap-3 p-4 lg:flex">
          {#if !hideVoteGauge}
            <VoteGauge id="vote-gauge" />
          {/if}

          {#if showHelpLink}
            {@render helpLink()}
          {/if}

          {#if !hideLanguageSelector}
            <LanguageSelector id="translate" />
          {/if}

          {#if !hideDiscussBtn}
            <Link
              button
              href="/arene"
              text={m['header.startDiscussion']()}
              class="whitespace-nowrap"
            />
          {/if}
        </div>
      </div>
    </div>
  </div>

  <dialog
    aria-labelledby="fr-modal-title-modal-menu"
    id="fr-modal-menu"
    class="fr-modal fr-header__menu"
  >
    <div class="fr-container lg:p-0!">
      <Button
        variant="tertiary-no-outline"
        text={m['words.close']()}
        title={m['closeModal']()}
        aria-controls="fr-modal-menu"
        class="fr-btn--close"
      />

      <div class="fr-header__menu-links after:mt-4! lg:hidden">
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

      {#if !hideDiscussBtn}
        <div class="mt-6! md:mt-0 lg:hidden">
          <Link
            button
            href="/arene"
            text={m['header.startDiscussion']()}
            class="w-full! whitespace-nowrap"
          />
        </div>
      {/if}
    </div>
  </dialog>
</header>
