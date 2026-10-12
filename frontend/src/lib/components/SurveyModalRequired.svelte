<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { page } from '$app/state'
  import { Modal } from '$components/dsfr'
  import { SurveyForm } from '$components/layout'
  import { m } from '$lib/i18n/messages'
  import { getSurveyContext } from '$lib/survey.svelte'

  const modalId = 'fr-modal-survey-signup'
  const survey = getSurveyContext()
  // The backend holds only chatting and voting, so the popup only opens where
  // those happen. It can be closed: settings, the privacy notice and account
  // erasure have to stay reachable for someone who will not answer, and the
  // next write brings the popup back anyway.
  const onChatPage = $derived(page.route.id === '/(arena)' || page.route.id === '/(arena)/[id]')

  function resetState() {
    survey.showRequiredSurvey = false
    invalidate('survey:signup')
  }
</script>

{#if survey.showRequiredSurvey && onChatPage}
  <button class="hidden" data-fr-opened={survey.showRequiredSurvey} aria-controls={modalId}>
    Hidden
  </button>

  <Modal
    id={modalId}
    titleId="form-{modalId}-title"
    sizeClass="fr-col-12 fr-col-md-8 fr-col-lg-6"
    onClose={resetState}
  >
    <SurveyForm
      id="form-{modalId}"
      title={m['survey.required.title']()}
      description={m['survey.required.description']()}
      onlyUnanswered
      class="mt-5"
      onSuccess={resetState}
    />
  </Modal>
{/if}
