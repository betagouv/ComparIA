<script lang="ts">
  import { Modal } from '$components/dsfr'
  import { getComparisonsContext, updateComparisonsContext } from '$lib/chatService.svelte'
  import SignInForm from './SignInForm.svelte'

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

<Modal
  id="fr-modal-signin"
  titleId="fr-modal-title-signin"
  sizeClass="fr-col-12 fr-col-md-6 fr-col-lg-5"
  contentClass="p-0! m-0!"
>
  <div class="-mt-12">
    <SignInForm {onSuccess} class="min-w-0" />
  </div>
</Modal>
