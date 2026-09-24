<script lang="ts">
  import { Modal } from '$components/dsfr'
  import { getAuthContext } from '$lib/auth.svelte'
  import { getComparisonsContext, updateComparisonsContext } from '$lib/chatService.svelte'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { m } from '$lib/i18n/messages'
  import { getSurveyContext } from '$lib/survey'
  import SignInForm from './SignInForm.svelte'

  const auth = getAuthContext()
  const comparisons = getComparisonsContext()
  const survey = getSurveyContext()

  let step = $state<'email' | 'code' | 'questions'>('email')

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
      survey.show = true
      survey.kind = 'signup'
    }
  }
</script>

<!-- Only the signed-out navbar can open it, and the form reads the visitor's
     consent on mount, so it is only kept mounted after sign-in for as long as
     the form still has questions to ask. -->
{#if !auth.user || step !== 'email'}
  <Modal
    id="fr-modal-signin"
    titleId="fr-modal-title-signin"
    sizeClass="fr-col-12 fr-col-md-6 fr-col-lg-5"
    contentClass="p-0! m-0!"
    {onClose}
  >
    <!-- The published terms describe how data is used, so the modal does not
         repeat it and risk saying something different. -->
    <div class="-mt-12">
      <SignInForm
        bind:step
        {onSuccess}
        onLegalNavigate={closeModal}
        titleId="fr-modal-title-signin"
        class="min-w-0"
      />
    </div>
  </Modal>
{/if}
