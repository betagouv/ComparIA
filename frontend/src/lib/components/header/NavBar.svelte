<script lang="ts">
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Button, Icon, Link } from '$components/dsfr'
  import { auth, logout } from '$lib/auth.svelte'
  import { m } from '$lib/i18n/messages'
  import type { ClassValue, HTMLAnchorAttributes } from 'svelte/elements'
  import { LanguageSelector, VoteGauge } from '.'

  type NavLink = { href: string; label: string; icon: string }
  const { navLinks, isAdmin = false }: { navLinks: NavLink[]; isAdmin?: boolean } = $props()

  let expanded = $state(true)
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
  class: linkClass,
  ...props
}: { icon: string; label: string } & HTMLAnchorAttributes)}
  {@const current = page.url.pathname === href}
  <Link
    {href}
    {...props}
    aria-current={current ? 'page' : undefined}
    class={[
      linkClass,
      current &&
        'bg-very-light-primary! text-primary! font-bold! border-primary ps-3! -ms-1 border-s-4'
    ]}
  >
    <span class={['gap-2 flex items-center', { 'lg:w-full lg:justify-center': !expanded }]}>
      <Icon {icon} block size={expanded ? 'sm' : 'md'} />
      <span class={{ 'lg:sr-only': !expanded }}>{label}</span>
    </span>
  </Link>
{/snippet}

{#snippet logo()}
  <div
    class={[
      'fr-enlarge-link gap-2 p-2 rounded-sm flex max-w-fit items-center',
      { 'lg:sr-only': !expanded }
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
  {#if !isAdmin}
    <div class={['gap-4 flex flex-col', { 'lg:hidden': !expanded }, classes]}>
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
  {/if}
{/snippet}

{#snippet footer(mode: 'desktop' | 'mobile' = 'desktop')}
  <div class="gap-2 flex flex-col">
    <div class="flex items-center justify-between">
      {@render renderLink({
        href: '/arena/settings',
        label: m['seo.titles.settings'](),
        icon: 'i-ri-settings-4-line',
        button: true,
        size: 'sm',
        variant: 'tertiary-no-outline',
        class: 'text-sm! text-black! -ms-3'
      })}

      <LanguageSelector id="translate-{mode}" class={{ 'lg:hidden': !expanded }} />
    </div>

    {#if auth.user}
      <div
        class="md:flex-row gap-1 lg:flex-col md:items-center lg:items-start -mt-1 md:justify-between flex flex-col"
      >
        <Button
          variant="tertiary-no-outline"
          size="sm"
          class="text-black! -ms-3"
          onclick={() => logout()}
        >
          <span class={['gap-2 flex items-center', { 'lg:w-full lg:justify-center': !expanded }]}>
            <Icon icon="i-ri-logout-box-r-line" block size={expanded ? 'sm' : 'md'} />
            <span class={{ 'lg:sr-only': !expanded }}>{m['auth.settings.logout']()}</span>
          </span>
        </Button>

        <p class={['text-sm mb-0! text-grey truncate', { 'lg:hidden': !expanded }]}>
          {auth.user.email}
        </p>
      </div>
    {/if}

    <!-- {@render helpLink()} -->

    <VoteGauge id="vote-gauge" class={{ hidden: !expanded }} />
  </div>
{/snippet}

<header
  id="main-header"
  class={[
    'fr-header shadow-md lg:shadow-none! lg:bg-very-light-primary! lg:b-e-[--grey-925-125] lg:b-e-1 lg:max-w-[250px] relative z-1 flex min-h-full! flex-col filter-none!',
    expanded ? 'lg:max-w-[250px]' : 'lg:max-w-[60px]'
  ]}
>
  <div class={['p-2 flex items-center', expanded ? 'justify-between' : 'justify-center']}>
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
        {@render footer('mobile')}
      </div>
    </div>
  </dialog>
</header>
