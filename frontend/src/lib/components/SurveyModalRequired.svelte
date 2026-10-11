<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Modal } from '$components/dsfr'
  import { SurveyForm } from '$components/layout'
  import { m } from '$lib/i18n/messages'
  import { getSurveyContext } from '$lib/survey.svelte'

  const modalId = 'fr-modal-survey-signup'
  const survey = getSurveyContext()

  function resetState() {
    survey.showRequiredSurvey = false
    invalidate('survey:signup')
  }
</script>

<button class="hidden" data-fr-opened={survey.showRequiredSurvey} aria-controls={modalId}>
  Hidden
</button>

<Modal
  id={modalId}
  locked
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
