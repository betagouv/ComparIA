<script lang="ts">
  import { page } from '$app/state'
  import { Modal, Tabs } from '$components/dsfr'
  import { SignInForm } from '$components/layout'
  import { getAuthContext } from '$lib/auth.svelte'
  import { getPlatformName } from '$lib/authContext.svelte'
  import { getComparisonsContext, updateComparisonsContext } from '$lib/chatService.svelte'
  import type { Step } from '$lib/components/layout/SignInForm.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { signInMethods } from '$lib/signInMethods'
  import { getSurveyContext } from '$lib/survey.svelte'
  import SSOSignIn from './SSOSignIn.svelte'

  const auth = getAuthContext()
  const comparisons = getComparisonsContext()
  const survey = getSurveyContext()
  const platformName = getPlatformName()

  let step = $state<Step>('email')
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

  // Closed on the questions: the sign-in itself already went through, so it
  // is finished like any other, minus the answers. Required ones come back in
  // their own popup, which the arena would ask for on the next write anyway.
  function onClose() {
    if (step !== 'questions') return
    step = 'email'
    updateComparisonsContext(comparisons)
    useToast(m['auth.success'](), 4000)
    if (auth.user && !auth.user.questionsAnswered) {
      survey.showRequiredSurvey = true
    }
  }
</script>

<!-- Only the signed-out navbar can open it, and the form reads the visitor's
     consent on mount, so keeping it mounted after sign-in only costs requests. -->
{#if !auth.user || step === 'questions'}
  <Modal
    id="fr-modal-signin"
    titleId="fr-modal-title-signin"
    sizeClass="fr-col-12 fr-col-md-6 fr-col-lg-5"
    contentClass="p-0! m-0!"
    {onClose}
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
                  bind:step
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
          bind:step
          {onSuccess}
          onLegalNavigate={closeModal}
          titleId="fr-modal-title-signin"
          class="min-w-0"
        />
      </div>
    {/if}
  </Modal>
{/if}
