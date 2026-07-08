<script lang="ts">
  import { goto } from '$app/navigation'
  import { page } from '$app/state'
  import { Button, Checkbox, Link } from '$components/dsfr'
  import { initAuth } from '$lib/auth.svelte'
  import { api } from '$lib/fastapi-client'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { onMount } from 'svelte'

  const token = $derived(page.params.token)

  let checkStatus = $state<'loading' | 'valid' | 'invalid'>('loading')
  let email = $state<string>()
  let consented = $state(false)
  let submitting = $state(false)
  let error = $state<string>()

  onMount(async () => {
    try {
      const result = await api.request<{ valid: boolean; email: string | null }>(
        `/auth/invite/${token}`
      )
      checkStatus = result.valid ? 'valid' : 'invalid'
      email = result.email ?? undefined
    } catch {
      checkStatus = 'invalid'
    }
  })

  async function accept() {
    submitting = true
    error = undefined
    try {
      await api.request('/auth/invite/accept', {
        method: 'POST',
        body: JSON.stringify({ token })
      })
      await initAuth()
      useToast(m['auth.success'](), 4000)
      goto('/arene')
    } catch (err) {
      error = (err as Error).message
      checkStatus = 'invalid'
    } finally {
      submitting = false
    }
  }
</script>

<svelte:head>
  <title>Invitation — compar:IA</title>
</svelte:head>

<div class="md:flex-row flex min-h-screen flex-col">
  <header class="px-8 py-10 gap-20 md:justify-center flex basis-1/2 flex-col">
    <div class="gap-2 flex items-center">
      <img src="/orgs/comparia.png" aria-hidden="true" alt="" class="h-[35px]" />
      <h1 class="font-bold text-base! mb-0!">{m['header.title']()}</h1>
    </div>

    <div>
      <h2 class="fr-h5 mb-4!">{m['invite.title']()}</h2>
      {#if email}
        <p class="text-sm! mb-0!">{email}</p>
      {/if}
    </div>
  </header>

  <main class="bg-light-grey md:flex md:items-center flex-auto basis-1/2">
    <div class="my-10 mx-8 md:max-w-[350px]">
      {#if checkStatus === 'invalid'}
        <p class="text-sm! mb-6!">{m['invite.invalid']()}</p>
        <Link button href="/login" text={m['invite.backToLogin']()} />
      {:else if checkStatus === 'valid'}
        <Checkbox
          id="invite-consent"
          class="text-xs!"
          bind:checked={consented}
          disabled={submitting}
          label={m['auth.modal.email.consent']()}
        />
        <Button
          text={submitting ? m['invite.accepting']() : m['invite.accept']()}
          disabled={!consented || submitting}
          onclick={accept}
          class="mt-4 block! w-full!"
        />
        {#if error}
          <p class="fr-error-text fr-text--sm mt-2!">{error}</p>
        {/if}
      {/if}
    </div>
  </main>
</div>
