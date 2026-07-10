<script lang="ts">
  import { goto } from '$app/navigation'
  import { page } from '$app/state'
  import SignInForm from '$components/SignInForm.svelte'
  import { env } from '$env/dynamic/public'
  import { auth, initAuth } from '$lib/auth.svelte'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  const redirectTo = $derived(page.url.searchParams.get('redirect') || '/arene')

  const loginTitle = env.PUBLIC_AUTH_LOGIN_TITLE || 'Bienvenue sur compar:IA'
  const loginDescription =
    env.PUBLIC_AUTH_LOGIN_DESCRIPTION ||
    "Comparez les modèles d'IA conversationnelle en aveugle et contribuez à l'évaluation de l'IA en Europe."

  onMount(() => {
    if (auth.user) goto(redirectTo)
    if (!auth.config) initAuth()
  })
</script>

<svelte:head>
  <title>Connexion — compar:IA</title>
</svelte:head>

<div class="md:flex-row flex min-h-screen flex-col">
  <header class="px-8 py-10 gap-20 md:justify-center flex basis-1/2 flex-col">
    <div class="gap-2 flex items-center">
      <img
        src={auth.config?.has_custom_logo ? api.getUrl('/auth/config/logo') : '/orgs/comparia.png'}
        aria-hidden="true"
        alt=""
        class="h-[35px]"
      />
      <h1 class="font-bold text-base! mb-0!">{auth.config?.platform_name || m['header.title']()}</h1>
    </div>

    <div>
      <h2 class="fr-h5 mb-4!">{loginTitle}</h2>
      <p class="text-sm! mb-0!">{loginDescription}</p>
    </div>
  </header>

  <main class="bg-light-grey md:flex md:items-center flex-auto basis-1/2">
    <SignInForm onSuccess={() => goto(redirectTo)} class="md:max-w-[350px]" />
  </main>
</div>
