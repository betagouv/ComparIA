<script lang="ts">
  import { Modal } from '$components/dsfr'
  import { getComparisonsContext, updateComparisonsContext } from '$lib/chatService.svelte'
  import { m } from '$lib/i18n/messages'
  import { sanitize } from '$lib/utils/commons'
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
  sizeClass="fr-col-12 fr-col-md-10"
  contentClass="p-0! m-0!"
>
  <div class="lg:flex -mt-12">
    <!-- Left column: form -->
    <SignInForm {onSuccess} class="min-w-[350px] flex-auto" />

    <!-- Right column: info -->
    <div class="px-8 py-10 bg-light-grey lg:pt-22 flex-initial">
      <h3 class="text-base! font-bold! mb-2!">{m['auth.modal.info.dataTitle']()}</h3>
      <p class="text-sm! mb-6!">{m['auth.modal.info.dataDesc']()}</p>

      <h3 class="text-base! font-bold! mb-2!">{m['auth.modal.info.datasetsTitle']()}</h3>
      <p class="text-sm! mb-2!">{@html sanitize(m['auth.modal.info.datasetsDesc']())}</p>
      <ul class="text-sm! my-2!">
        <li>{m['auth.modal.info.neverName']()}</li>
        <li>{m['auth.modal.info.neverAddress']()}</li>
        <li>{m['auth.modal.info.neverPhone']()}</li>
        <li>{m['auth.modal.info.neverPersonal']()}</li>
        <li>{m['auth.modal.info.neverOther']()}</li>
      </ul>
      <p class="text-sm! mb-0!">{m['auth.modal.info.emailPrivacy']()}</p>
    </div>
  </div>
</Modal>
