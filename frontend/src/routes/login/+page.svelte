<script lang="ts">
  import { goto } from '$app/navigation'
  import { match, resolve } from '$app/paths'
  import { page } from '$app/state'
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
  // Set by the invite page once an admin's invite left only the authenticator to check.
  const startAtTotp = page.url.searchParams.get('step') === 'totp'

  async function onSuccess() {
    const redirect = page.url.searchParams.get('redirect')
    if (redirect && (await match(redirect))) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      goto(resolve(redirect as any))
    } else {
      goto(resolve('/'))
    }
  }
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
    <SignInForm {onSuccess} {startAtTotp} class="md:max-w-[350px]" />
  </main>
</div>
