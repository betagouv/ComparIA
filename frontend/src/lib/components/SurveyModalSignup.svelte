<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Modal } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'
  import { getSurveyContext } from '$lib/survey'
  import SurveyFormSignup from './SurveyFormSignup.svelte'

  const modalId = 'fr-modal-survey-signup'
  const survey = getSurveyContext()
  const opened = $derived(survey.show && survey.kind === 'signup')

  function resetState() {
    survey.show = false
    survey.kind = null
    invalidate('survey:signup')
  }
</script>

<button class="hidden" data-fr-opened={opened} aria-controls={modalId}>Hidden</button>

<Modal
  id={modalId}
  locked
  titleId="form-{modalId}-title"
  sizeClass="fr-col-12 fr-col-md-8 fr-col-lg-6"
  onClose={resetState}
>
  <SurveyFormSignup
    id="form-{modalId}"
    title={m['survey.afterVote.title']()}
    questions={survey.signupQuestions}
    answers={survey.signupAnswers}
    class="mt-5"
    onSuccess={resetState}
  />
</Modal>
