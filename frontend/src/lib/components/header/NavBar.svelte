<script lang="ts">
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Button, Icon, Link } from '$components/dsfr'
  import { auth, logout } from '$lib/auth.svelte'
  import { m } from '$lib/i18n/messages'
  import type { ClassValue, HTMLAnchorAttributes } from 'svelte/elements'
  import { VoteGauge } from '.'

  const navLinks = [
    { href: '/arene', label: m['header.chatbot.newDiscussion'](), icon: 'i-ri-chat-new-line' },
    { href: '/arene/ranking', label: m['seo.titles.ranking'](), icon: 'i-ri-trophy-line' },
    { href: '/arene/modeles', label: m['seo.titles.modeles'](), icon: 'i-ri-stack-line' }
    // { href: '/dataviz', label: 'FIXME' },
  ] as const

  let expanded = $state(true)
  let settingsOpen = $state(false)
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

{#snippet renderLink({
  href,
  icon,
  label,
  ...props
}: { icon: string; label: string } & HTMLAnchorAttributes)}
  <Link {href} {...props} aria-current={page.url.pathname === href}>
    <span class={['gap-2 flex items-center', { 'w-full justify-center': !expanded }]}>
      <Icon {icon} block size={expanded ? 'sm' : 'md'} />
      <span class={{ 'sr-only': !expanded }}>{label}</span>
    </span>
  </Link>
{/snippet}

{#snippet logo()}
  <div
    class={[
      'fr-enlarge-link gap-2 p-2 rounded-sm flex max-w-fit items-center',
      { 'sr-only': !expanded }
    ]}
  >
    <img src="/orgs/comparia.png" aria-hidden="true" alt="" class="h-[35px]" />
    <a
      href={resolve('/')}
      title={m['header.homeTitle']()}
      class="font-bold text-lg text-[--text-title-grey]"
    >
      {m['header.title']()}
    </a>
  </div>
{/snippet}

{#snippet discussions(classes?: ClassValue)}
  <div class={['gap-4 flex flex-col', { hidden: !expanded }, classes]}>
    <p class="text-sm mb-0! text-grey">
      {m['auth.discussions.title']()}
    </p>
    {#if !auth.user}
      <p class="text-sm mb-0! text-black">
        {m['auth.discussions.prompt']()}
      </p>
      <Button
        variant="tertiary"
        text={m['auth.discussions.signIn']()}
        icon="user-line"
        size="sm"
        aria-controls="fr-modal-signin"
        data-fr-opened="false"
        class="block w-full!"
      />
    {/if}
  </div>
{/snippet}

{#snippet footer()}
  <div class="gap-2 flex flex-col">
    <div class="relative">
      {#if settingsOpen && auth.user}
        <div class="absolute bottom-full left-0 right-0 mb-1 bg-white shadow-md border border-[--grey-925-125] rounded-sm">
          <button
            class="fr-btn fr-btn--tertiary-no-outline fr-btn--sm w-full! justify-start!"
            onclick={() => { settingsOpen = false; logout() }}
          >
            <span class="fr-icon-logout-box-r-line fr-btn__icon fr-btn__icon--left" aria-hidden="true"></span>
            {m['auth.settings.logout']()}
          </button>
        </div>
      {/if}

      <button
        class="fr-btn fr-btn--tertiary-no-outline fr-btn--sm w-full! justify-start! -ml-2!"
        onclick={() => (settingsOpen = !settingsOpen)}
        aria-expanded={settingsOpen}
      >
        <span class="fr-icon-settings-5-line fr-btn__icon fr-btn__icon--left" aria-hidden="true"></span>
        <span class={{ 'sr-only': !expanded }}>{m['auth.settings.title']()}</span>
        {#if expanded}
          <span class={['fr-icon--sm ml-auto', settingsOpen ? 'fr-icon-arrow-up-s-line' : 'fr-icon-arrow-down-s-line']} aria-hidden="true"></span>
        {/if}
      </button>

      {#if expanded && auth.user}
        <p class="fr-text--xs mb-0! text-[--text-mention-grey] truncate">{auth.user.email}</p>
      {/if}
    </div>

    <div class={{ hidden: !expanded }}>
      <!-- <LanguageSelector id="translate" />
      {@render helpLink()} -->
      <VoteGauge id="vote-gauge" />
    </div>
  </div>
{/snippet}

<header
  id="main-header"
  class={[
    'fr-header shadow-md lg:shadow-none! lg:bg-very-light-primary! lg:b-e-[--grey-925-125] lg:b-e-1 lg:max-w-[250px] relative z-1 flex min-h-full! flex-col filter-none!',
    expanded ? 'lg:max-w-[250px]' : 'lg:max-w-[60px]'
  ]}
>
  <div class={['p-2 flex items-center ', expanded ? 'justify-between' : 'justify-center']}>
    {@render logo()}

    <Button
      variant="tertiary-no-outline"
      size="sm"
      class="px-1! lg:block! hidden!"
      onclick={() => (expanded = !expanded)}
    >
      <Icon
        icon={expanded ? 'i-ri-layout-left-2-line' : 'i-ri-layout-left-line'}
        class="text-grey"
        size="sm"
        block
        aria-label={m[expanded ? 'actions.reduceMenu' : 'actions.expandMenu']()}
      />
    </Button>

    <div class="fr-header__navbar mt-0! self-auto!">
      <button
        class="fr-btn fr-btn--menu -ms-1! me-3!"
        data-fr-opened="false"
        aria-controls="fr-modal-menu"
        aria-haspopup="menu"
        title={m['header.menu']()}
      >
        {m['header.menu']()}
      </button>
    </div>
  </div>

  <div class="lg:flex hidden grow flex-col">
    <nav class="py-4">
      <ul class="fr-sidemenu__list">
        {#each navLinks as link (link.href)}
          <li class="fr-sidemenu__item">
            {@render renderLink({
              ...link,
              class:
                'text-sm! text-black! fr-sidemenu__link font-normal! py-2! before:content-none!'
            })}
          </li>
        {/each}
      </ul>
    </nav>

    {@render discussions('mt-3 px-4')}

    <div class="b-t-[--grey-925-125] b-t-1 px-4 py-5 mt-auto">
      {@render footer()}
    </div>
  </div>

  <dialog
    aria-labelledby="fr-modal-title-modal-menu"
    id="fr-modal-menu"
    class="fr-modal fr-header__menu lg:hidden!"
  >
    <div class="fr-container pb-0! flex flex-col">
      <div class="flex items-center justify-between">
        {@render logo()}
        <Button
          variant="tertiary-no-outline"
          text={m['words.close']()}
          title={m['closeModal']()}
          aria-controls="fr-modal-menu"
          class="fr-btn--close"
        />
      </div>
      <div class="fr-header__menu-links"></div>

      <nav class="fr-nav" data-fr-js-navigation="true">
        <ul class="fr-nav__list fr-container">
          {#each navLinks as link (link.href)}
            <li class="fr-nav__item" data-fr-js-navigation-item="true">
              {@render renderLink({
                ...link,
                target: '_self',
                class: 'fr-nav__link text-black! font-normal!',
                'data-fr-js-modal-button': 'true',
                'aria-controls': 'modal-header__menu'
              })}
            </li>
          {/each}
        </ul>
      </nav>

      {@render discussions('b-t-[--grey-925-125] b-t-1 py-4 gap-2!')}

      <div class="fr-header__menu-links mt-auto"></div>
      <div class="bottom-0 pb-5 pt-2 bg-white sticky">
        {@render footer()}
      </div>
    </div>
  </dialog>
</header>
