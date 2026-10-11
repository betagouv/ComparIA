<script lang="ts">
  import { Modal } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getSurveyContext } from '$lib/survey.svelte'
  import { SurveyForm } from './layout'

  const modalId = 'fr-modal-survey'
  const survey = getSurveyContext()

  function closeModal() {
    const el = document.getElementById(modalId)
    if (el) {
      // @ts-expect-error - DSFR is globally available
      window.dsfr(el).modal.conceal()
    }
  }
</script>

{#if survey.showSurveyCard}
  <Modal
    id={modalId}
    titleId="form-{modalId}-title"
    sizeClass="fr-col-12 fr-col-md-8 fr-col-lg-6"
    teleport
  >
    <SurveyForm
      id="form-{modalId}"
      title={m['survey.afterVote.title']()}
      description={m['survey.afterVote.description']()}
      onlyUnanswered
      dismissible
      {modalId}
      class="mt-5"
      onSuccess={() => closeModal()}
    />
  </Modal>
{/if}
