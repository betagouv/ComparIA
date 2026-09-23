<script lang="ts">
  import { page } from '$app/state'
  import { Modal, Tabs } from '$components/dsfr'
  import { getAuthContext } from '$lib/auth.svelte'
  import { getPlatformName } from '$lib/authContext.svelte'
  import { getComparisonsContext, updateComparisonsContext } from '$lib/chatService.svelte'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import SignInForm from './SignInForm.svelte'
  import SSOSignIn from './SSOSignIn.svelte'

  const auth = getAuthContext()
  const comparisons = getComparisonsContext()
  const platformName = getPlatformName()

  // Same derivation as the login page: one tab per enabled auth method, no
  // tabs at all when only one is available.
  const oidcEnabled = $derived(auth.config?.oidc_enabled ?? false)
  const emailEnabled = $derived(auth.config?.methods?.includes('email_code') ?? true)
  const oidcLabel = $derived(auth.config?.oidc_button_label || m['auth.oidc.buttonFallback']())
  const oidcLogoUrl = $derived(
    auth.config?.oidc_has_button_logo ? api.getUrl('/auth/config/oidc/logo') : null
  )
  // Brings a visitor who signs in through the provider back to the page they
  // opened the modal from.
  const redirect = $derived(page.url.pathname + page.url.search)
  const bothMethods = $derived(oidcEnabled && emailEnabled)
  const tabs = $derived.by(() => {
    const result: { id: string; label: string }[] = []
    if (emailEnabled) result.push({ id: 'email', label: m['auth.login.tabEmail']() })
    if (oidcEnabled) result.push({ id: 'sso', label: m['auth.login.tabSso']() })
    return result
  })

  function closeModal() {
    const el = document.getElementById('fr-modal-signin')
    if (el) {
      // @ts-expect-error - DSFR is globally available
      window.dsfr(el).modal.conceal()
    }
  }

  async function onSuccess() {
    closeModal()
    updateComparisonsContext(comparisons)
  }
</script>

<!-- Only the signed-out navbar can open it, and the form reads the visitor's
     consent on mount, so keeping it mounted after sign-in only costs requests. -->
{#if !auth.user}
  <Modal
    id="fr-modal-signin"
    titleId="fr-modal-title-signin"
    sizeClass="fr-col-12 fr-col-md-6 fr-col-lg-5"
    contentClass="p-0! m-0!"
  >
    <!-- The published terms describe how data is used, so the modal does not
         repeat it and risk saying something different. -->
    {#if bothMethods || !emailEnabled}
      <div class="-mt-12">
        <h2 id="fr-modal-title-signin" class="fr-h4 text-primary! mb-4!">
          {m['auth.modal.email.title']()}
        </h2>
        <p class="text-xs! mb-6! text-grey">
          {m['auth.modal.email.subtitle']({ platformName })}
        </p>

        {#if bothMethods}
          <Tabs {tabs} label={m['auth.login.tabsLabel']()}>
            {#snippet tab(tab)}
              {#if tab.id === 'email'}
                <SignInForm
                  {onSuccess}
                  onLegalNavigate={closeModal}
                  hideHeader
                  class="my-0! mx-0! min-w-0"
                />
              {:else}
                <SSOSignIn
                  {oidcLabel}
                  {oidcLogoUrl}
                  {redirect}
                  onLegalNavigate={closeModal}
                  class="my-0! mx-0!"
                />
              {/if}
            {/snippet}
          </Tabs>
        {:else}
          <SSOSignIn
            {oidcLabel}
            {oidcLogoUrl}
            {redirect}
            onLegalNavigate={closeModal}
            class="my-0! mx-0!"
          />
        {/if}
      </div>
    {:else}
      <SignInForm
        {onSuccess}
        onLegalNavigate={closeModal}
        titleId="fr-modal-title-signin"
        class="min-w-0"
      />
    {/if}
  </Modal>
{/if}
