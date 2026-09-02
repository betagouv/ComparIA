<script lang="ts">
  import { Modal } from '$components/dsfr'
  import { getAuthContext } from '$lib/auth.svelte'
  import { getComparisonsContext, updateComparisonsContext } from '$lib/chatService.svelte'
  import SignInForm from './SignInForm.svelte'

  const auth = getAuthContext()
  const comparisons = getComparisonsContext()

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
    <div class="-mt-12">
      <SignInForm
        {onSuccess}
        onLegalNavigate={closeModal}
        titleId="fr-modal-title-signin"
        class="min-w-0"
      />
    </div>
  </Modal>
{/if}
