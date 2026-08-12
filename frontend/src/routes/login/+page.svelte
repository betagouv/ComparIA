<script lang="ts">
  import { goto } from '$app/navigation'
  import { match, resolve } from '$app/paths'
  import { page } from '$app/state'
  import { Alert, Link } from '$components/dsfr'
  import SeoHead from '$components/SEOHead.svelte'
  import SignInForm from '$components/SignInForm.svelte'
  import { env } from '$env/dynamic/public'
  import { getAuthContext } from '$lib/auth.svelte'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'

  const auth = getAuthContext()
  const platformName = $derived(auth.config?.platform_name || m['header.title']())
  const loginTitle = $derived(
    env.PUBLIC_AUTH_LOGIN_TITLE || m['auth.login.title']({ platformName })
  )
  const loginDescription = $derived(
    env.PUBLIC_AUTH_LOGIN_DESCRIPTION || m['auth.login.description']()
  )

  async function onSuccess() {
    const redirect = page.url.searchParams.get('redirect')
    if (redirect && (await match(redirect))) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      goto(resolve(redirect as any))
    } else {
      goto(resolve('/'))
    }
  }

  // The server derives `oidc_enabled` from `methods` + a complete provider
  // config, so the button only renders when OIDC would actually work. The
  // email form is hidden when OIDC is the only enabled method.
  const oidcEnabled = $derived(auth.config?.oidc_enabled ?? false)
  const emailEnabled = $derived(auth.config?.methods?.includes('email_code') ?? true)
  const oidcLabel = $derived(auth.config?.oidc_button_label || m['auth.oidc.buttonFallback']())
  const oidcLogoUrl = $derived(
    auth.config?.oidc_has_button_logo ? api.getUrl('/auth/config/oidc/logo') : null
  )

  // The OIDC callback redirects back here with ?error=<reason> on any failure
  // (ticket 05). Render a clear message so the redirect isn't a silent no-op.
  // An explicit code → message-function map keeps the lookup type-safe against
  // the generated Paraglide `m` module (dynamic key indexing on `m` is not
  // allowed by its types).
  const oidcErrorMessages: Record<string, () => string> = {
    domain_not_allowed: () => m['auth.oidc.error.domain_not_allowed'](),
    invalid_nonce: () => m['auth.oidc.error.invalid_nonce'](),
    invalid_state: () => m['auth.oidc.error.invalid_state'](),
    missing_code: () => m['auth.oidc.error.missing_code'](),
    no_email: () => m['auth.oidc.error.no_email'](),
    oidc_unavailable: () => m['auth.oidc.error.oidc_unavailable'](),
    provider_error: () => m['auth.oidc.error.provider_error']()
  }
  const errorCode = $derived(page.url.searchParams.get('error'))
  const errorText = $derived(
    errorCode && oidcErrorMessages[errorCode] ? oidcErrorMessages[errorCode]() : null
  )
</script>

<SeoHead title={m['seo.titles.login']()} />

<div class="md:flex-row flex min-h-screen flex-col">
  <header class="px-8 py-10 gap-20 md:justify-center flex basis-1/2 flex-col">
    <div class="gap-2 flex items-center">
      <img
        src={auth.config?.has_custom_logo ? api.getUrl('/auth/config/logo') : '/orgs/comparia.png'}
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
    <div class="my-10 mx-8 md:max-w-[350px] w-full">
      {#if errorText}
        <Alert title={errorText} variant="error" class="mb-6!" />
      {/if}

      {#if oidcEnabled}
        <Link
          href="/auth/oidc/login"
          button
          variant="secondary"
          class="block w-full! justify-center"
        >
          <span class="gap-2 inline-flex items-center justify-center">
            {#if oidcLogoUrl}
              <img src={oidcLogoUrl} alt="" class="h-5" />
            {/if}
            {oidcLabel}
          </span>
        </Link>
      {/if}

      {#if oidcEnabled && emailEnabled}
        <p class="text-xs! text-grey my-4! mb-0! text-center">{m['auth.oidc.or']()}</p>
      {/if}

      {#if emailEnabled}
        <SignInForm {onSuccess} class="my-0! mx-0!" />
      {/if}
    </div>
  </main>
</div>
