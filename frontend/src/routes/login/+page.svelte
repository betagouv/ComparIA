<script lang="ts">
  import { goto } from '$app/navigation'
  import { match, resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Alert, Tabs } from '$components/dsfr'
  import { SeoHead, SignInForm } from '$components/layout'
  import SSOSignIn from '$components/SSOSignIn.svelte'
  import { env } from '$env/dynamic/public'
  import { getAuthContext } from '$lib/auth.svelte'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import { signInMethods } from '$lib/signInMethods'

  const auth = getAuthContext()
  const platformName = $derived(auth.config?.platform_name || m['header.title']())
  const loginTitle = $derived(
    env.PUBLIC_AUTH_LOGIN_TITLE || m['auth.login.title']({ platformName })
  )
  const loginDescription = $derived(
    env.PUBLIC_AUTH_LOGIN_DESCRIPTION || m['auth.login.description']()
  )
  // Set by the invite page once an admin's invite left only the authenticator to check.
  let atTotpStep = $state(page.url.searchParams.get('step') === 'totp')
  // Why the visitor was sent back to the SSO button, when the authenticator
  // step expired on an instance without email codes.
  let expiredNotice = $state<string>()

  function onChallengeExpired(message: string) {
    atTotpStep = false
    expiredNotice = message
  }

  async function onSuccess() {
    const redirect = page.url.searchParams.get('redirect')
    if (redirect && (await match(redirect))) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      goto(resolve(redirect as any))
    } else {
      goto(resolve('/'))
    }
  }

  const methods = $derived(signInMethods(auth.config))
  // The OIDC callback redirects back here with ?error=<reason> on any failure.
  // Render a clear message so the redirect isn't a silent no-op.
  // An explicit code → message-function map keeps the lookup type-safe against
  // the generated Paraglide `m` module (dynamic key indexing on `m` is not
  // allowed by its types).
  const oidcErrorMessages: Record<string, () => string> = {
    account_unavailable: () => m['auth.oidc.error.account_unavailable'](),
    domain_not_allowed: () => m['auth.oidc.error.domain_not_allowed'](),
    email_not_verified: () => m['auth.oidc.error.email_not_verified'](),
    invalid_nonce: () => m['auth.oidc.error.invalid_nonce'](),
    invalid_state: () => m['auth.oidc.error.invalid_state'](),
    missing_code: () => m['auth.oidc.error.missing_code'](),
    no_email: () => m['auth.oidc.error.no_email'](),
    oidc_unavailable: () => m['auth.oidc.error.oidc_unavailable'](),
    provider_error: () => m['auth.oidc.error.provider_error'](),
    rate_limited: () => m['auth.oidc.error.rate_limited'](),
    terms_required: () => m['auth.oidc.error.terms_required']()
  }
  const errorCode = $derived(page.url.searchParams.get('error'))
  const redirect = $derived(page.url.searchParams.get('redirect'))
  const errorText = $derived(
    expiredNotice ??
      (errorCode && oidcErrorMessages[errorCode] ? oidcErrorMessages[errorCode]() : null)
  )
</script>

<SeoHead title={m['seo.titles.login']()} />

<div class="md:flex-row flex min-h-screen flex-col">
  <header class="px-8 py-10 gap-20 md:justify-center flex basis-1/2 flex-col">
    <div class="gap-2 flex items-center">
      <img
        src={auth.config?.has_custom_logo
          ? api.getUrl('/auth/config/logo', { v: auth.config.logo_version ?? '' })
          : '/orgs/comparia.png'}
        aria-hidden="true"
        alt=""
        class="h-[35px]"
      />
      <h1 class="font-bold text-base! mb-0!">{platformName}</h1>
    </div>

    <div>
      <h2 class="fr-h5 mb-4!">{loginTitle}</h2>
      <p class="text-sm! mb-0!">{loginDescription}</p>
    </div>
  </header>

  <main class="bg-light-grey md:flex md:items-center flex-auto basis-1/2">
    <div class="my-10 mx-8 md:max-w-[350px] md:w-full">
      <!-- One heading for every method mix, like the modal, instead of the
           email form's own which disappears once there are tabs. -->
      <h2 class="fr-h4 text-primary! mb-4!">{m['auth.modal.email.title']()}</h2>
      <p class="text-xs! mb-6! text-grey">{m['auth.modal.email.subtitle']({ platformName })}</p>

      {#if errorText}
        <Alert title={errorText} variant="error" small role="alert" class="mb-6!" />
      {/if}

      {#if atTotpStep}
        <!-- The first factor already passed, by email or through the SSO
             provider: only the authenticator is left, whatever the methods. -->
        <SignInForm {onSuccess} startAtTotp {onChallengeExpired} hideHeader class="py-0! px-0!" />
      {:else if methods.bothMethods}
        <Tabs
          tabs={methods.tabs}
          label={m['auth.login.tabsLabel']()}
          initialId={errorText ? 'sso' : 'email'}
        >
          {#snippet tab(tab)}
            {#if tab.id === 'email'}
              <SignInForm {onSuccess} hideHeader class="py-0! px-0!" />
            {:else}
              <SSOSignIn
                oidcLabel={methods.oidcLabel}
                oidcLogoUrl={methods.oidcLogoUrl}
                {redirect}
                class="my-0! mx-0!"
              />
            {/if}
          {/snippet}
        </Tabs>
      {:else if methods.emailEnabled}
        <SignInForm {onSuccess} hideHeader class="py-0! px-0!" />
      {:else if methods.oidcEnabled}
        <SSOSignIn
          oidcLabel={methods.oidcLabel}
          oidcLogoUrl={methods.oidcLogoUrl}
          {redirect}
          class="my-0! mx-0!"
        />
      {/if}
    </div>
  </main>
</div>
