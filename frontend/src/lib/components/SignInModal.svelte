<script lang="ts">
  import { page } from '$app/state'
  import { Modal, Tabs } from '$components/dsfr'
  import { SignInForm } from '$components/layout'
  import { getAuthContext } from '$lib/auth.svelte'
  import { getPlatformName } from '$lib/authContext.svelte'
  import { getComparisonsContext, updateComparisonsContext } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { signInMethods } from '$lib/signInMethods'
  import SSOSignIn from './SSOSignIn.svelte'

  const auth = getAuthContext()
  const comparisons = getComparisonsContext()
  const platformName = getPlatformName()

  const methods = $derived(signInMethods(auth.config))
  // Brings a visitor who signs in through the provider back to the page they
  // opened the modal from.
  const redirect = $derived(page.url.pathname + page.url.search)

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
    {#if methods.bothMethods || !methods.emailEnabled}
      <!-- Same inset as SignInForm's own wrapper, which the modal content
           relies on since it has no padding of its own. -->
      <div class="-mt-12 mx-8 mb-10 pt-10">
        <h2 id="fr-modal-title-signin" class="fr-h4 text-primary! mb-4!">
          {m['auth.modal.email.title']()}
        </h2>
        <p class="text-xs! mb-6! text-grey">
          {m['auth.modal.email.subtitle']({ platformName })}
        </p>

        {#if methods.bothMethods}
          <Tabs tabs={methods.tabs} label={m['auth.login.tabsLabel']()}>
            {#snippet tab(tab)}
              {#if tab.id === 'email'}
                <SignInForm
                  {onSuccess}
                  onLegalNavigate={closeModal}
                  hideHeader
                  class="py-0! px-0! min-w-0"
                />
              {:else}
                <SSOSignIn
                  oidcLabel={methods.oidcLabel}
                  oidcLogoUrl={methods.oidcLogoUrl}
                  {redirect}
                  onLegalNavigate={closeModal}
                  class="my-0! mx-0!"
                />
              {/if}
            {/snippet}
          </Tabs>
        {:else}
          <SSOSignIn
            oidcLabel={methods.oidcLabel}
            oidcLogoUrl={methods.oidcLogoUrl}
            {redirect}
            onLegalNavigate={closeModal}
            class="my-0! mx-0!"
          />
        {/if}
      </div>
    {:else}
      <div class="-mt-12">
        <SignInForm
          {onSuccess}
          onLegalNavigate={closeModal}
          titleId="fr-modal-title-signin"
          class="min-w-0"
        />
      </div>
    {/if}
  </Modal>
{/if}
