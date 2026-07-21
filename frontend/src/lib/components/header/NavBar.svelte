<script module lang="ts">
  export type NavLink = {
    label: string
    icon: string
    isCurrent?: (href: string) => boolean
  } & LinkProps
</script>

<script lang="ts">
  import { resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Button, Icon, Link } from '$components/dsfr'
  import type { LinkProps } from '$components/dsfr/Link.svelte'
  import { getAuthContext, logout } from '$lib/auth.svelte'
  import { getComparisonsContext } from '$lib/chatService.svelte'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import type { HTMLAnchorAttributes } from 'svelte/elements'
  import { History, LanguageSelector, VoteGauge } from '.'

  const { navLinks, isAdmin = false }: { navLinks: NavLink[]; isAdmin?: boolean } = $props()

  const auth = getAuthContext()
  // Admin navigation never gains an arena context during its lifetime.
  // svelte-ignore state_referenced_locally
  const comparisons = isAdmin ? undefined : getComparisonsContext()
  let expanded = $state(true)
  let legalMenuOpen = $state(false)

  function handleLegalMenuKeydown(event: KeyboardEvent, mode: 'desktop' | 'mobile') {
    if (event.key !== 'Escape') return
    legalMenuOpen = false
    document.getElementById(`legal-menu-trigger-${mode}`)?.focus()
  }

  const connectionBtnProps = $derived(
    auth.user
      ? {
          text: m['auth.settings.logout'](),
          icon: 'i-ri-logout-box-r-line',
          onclick: () => logout(auth, comparisons)
        }
      : {
          text: m['auth.discussions.signIn'](),
          icon: 'i-ri-login-box-line',
          'aria-controls': 'fr-modal-signin',
          'data-fr-opened': 'false'
        }
  )
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
  isCurrent,
  class: linkClass,
  ...props
}: NavLink & HTMLAnchorAttributes)}
  {@const current = isCurrent ? isCurrent(href!) : page.url.pathname === href}
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
    <img
      src={auth.config?.has_custom_logo ? api.getUrl('/auth/config/logo') : '/orgs/comparia.png'}
      aria-hidden="true"
      alt=""
      class="h-[35px]"
    />
    <a
      href={resolve('/')}
      title={m['header.homeTitle']()}
      class="font-bold text-lg text-[--text-title-grey]"
    >
      {auth.config?.platform_name || m['header.title']()}
    </a>
  </div>
{/snippet}

{#snippet legalMenu(mode: 'desktop' | 'mobile')}
  <div class="relative">
    <button
      id="legal-menu-trigger-{mode}"
      type="button"
      aria-expanded={legalMenuOpen}
      aria-controls="legal-menu-{mode}"
      onclick={() => (legalMenuOpen = !legalMenuOpen)}
      class={[
        'text-sm! text-grey! -ms-3 px-3 py-2 rounded gap-2 flex cursor-pointer list-none items-center hover:bg-[--background-contrast-grey] [&::-webkit-details-marker]:hidden',
        { 'lg:justify-center': !expanded }
      ]}
    >
      <Icon icon="i-ri-scales-3-line" block size={expanded ? 'sm' : 'md'} />
      <span class={{ 'lg:sr-only': !expanded }}>Informations légales</span>
      <Icon
        icon="i-ri-arrow-up-s-line"
        block
        size="sm"
        class={[
          'ms-auto transition-transform',
          { 'rotate-180': legalMenuOpen, 'lg:hidden': !expanded }
        ]}
      />
    </button>

    <nav
      id="legal-menu-{mode}"
      aria-label="Informations légales"
      hidden={!legalMenuOpen}
      class="lg:absolute lg:bottom-full lg:left-0 lg:w-[290px] lg:mb-2 p-3 bg-white rounded shadow-lg z-100 border border-[--border-default-grey]"
    >
      <p class="fr-text--sm font-bold mb-2!">Informations légales</p>
      <ul class="fr-raw-list gap-2 flex flex-col items-start">
        <li>
          <Link
            href={resolve('/arene/donnees-personnelles')}
            text="Données personnelles et confidentialité"
            size="sm"
            onclick={() => (legalMenuOpen = false)}
            onkeydown={(event) => handleLegalMenuKeydown(event, mode)}
          />
        </li>
        <li>
          <Link
            href={resolve('/arene/modalites')}
            text="Conditions générales d’utilisation"
            size="sm"
            onclick={() => (legalMenuOpen = false)}
            onkeydown={(event) => handleLegalMenuKeydown(event, mode)}
          />
        </li>
        <li>
          <Link
            href={resolve('/accessibilite')}
            text="Accessibilité : non conforme"
            size="sm"
            onclick={() => (legalMenuOpen = false)}
            onkeydown={(event) => handleLegalMenuKeydown(event, mode)}
          />
        </li>
        <li>
          <Link
            href={resolve('/mentions-legales')}
            text="Mentions légales"
            size="sm"
            onclick={() => (legalMenuOpen = false)}
            onkeydown={(event) => handleLegalMenuKeydown(event, mode)}
          />
        </li>
      </ul>
    </nav>
  </div>
{/snippet}

{#snippet footer(mode: 'desktop' | 'mobile' = 'desktop')}
  <div class="gap-2 flex flex-col">
    <div
      class={[
        'gap-2 flex items-center justify-between',
        { 'lg:flex-col lg:justify-center': !expanded }
      ]}
    >
      <span class={['text-sm text-grey', { 'lg:sr-only': !expanded }]}>Mon compte</span>

      <div class={['gap-1 flex items-center', { 'lg:flex-col': !expanded }]}>
        <Link
          href={resolve('/arene/parametres')}
          button
          iconOnly
          size="xs"
          variant="tertiary-no-outline"
          aria-label="Paramètres"
          title="Paramètres"
        >
          <Icon icon="i-ri-settings-4-line" block size="sm" />
        </Link>

        <Button
          variant="tertiary-no-outline"
          size="xs"
          iconOnly
          {...connectionBtnProps}
          icon={undefined}
          text={undefined}
          aria-label={connectionBtnProps.text}
          title={connectionBtnProps.text}
        >
          <Icon icon={connectionBtnProps.icon} block size="sm" />
        </Button>
      </div>
    </div>

    <div class="flex justify-end">
      <LanguageSelector id="translate-{mode}" class={{ 'lg:hidden': !expanded }} />
    </div>

    <!-- {@render helpLink()} -->

    <VoteGauge id="vote-gauge" class={{ 'lg:hidden': !expanded }} />

    {@render legalMenu(mode)}
  </div>
{/snippet}

<header
  id="main-header"
  class={[
    'fr-header lg:max-h-screen shadow-md lg:shadow-none! lg:bg-very-light-primary! lg:b-e-[--grey-925-125] lg:b-e-1 lg:max-w-[250px] flex min-h-full! flex-col filter-none!',
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

  <div class="lg:flex min-h-0 hidden flex-auto flex-col">
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

    {#if !isAdmin}
      <History {expanded} />
    {/if}

    <div class="b-t-[--grey-925-125] b-t-1 px-4 py-5 mt-auto">
      {@render footer()}
    </div>
  </div>

  <dialog
    aria-labelledby="fr-modal-title-modal-menu"
    id="fr-modal-menu"
    class="fr-modal fr-header__menu lg:hidden!"
  >
    <div class="fr-container p-0! gap-4 flex flex-col">
      <div class="p-2 flex items-center justify-between border-b border-[--grey-925-125]">
        {@render logo()}
        <Button
          variant="tertiary-no-outline"
          text={m['words.close']()}
          title={m['closeModal']()}
          aria-controls="fr-modal-menu"
          class="fr-btn--close"
        />
      </div>

      <nav class="fr-nav border-b border-[--grey-925-125]">
        <ul class="fr-nav__list fr-container">
          {#each navLinks as link (link.href)}
            <li class="fr-nav__item">
              {@render renderLink({
                ...link,
                class: 'fr-nav__link text-black! font-normal!',
                'data-fr-js-modal-button': 'true',
                'aria-controls': 'fr-modal-menu'
              })}
            </li>
          {/each}
        </ul>
      </nav>

      {#if !isAdmin}
        <History mode="mobile" expanded={true} />
      {/if}

      <div class="bottom-0 pb-5 p-4 bg-white sticky mt-auto border-t border-[--grey-925-125]">
        {@render footer('mobile')}
      </div>
    </div>
  </dialog>
</header>
