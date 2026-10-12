<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Modal } from '$components/dsfr'
  import { getAuthContext } from '$lib/auth.svelte'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import { getSurveyContext } from '$lib/survey.svelte'
  import { SurveyForm } from './layout'

  const modalId = 'fr-modal-survey'
  const auth = getAuthContext()
  const survey = getSurveyContext()

  // The form's own submit already counted this showing, so the close that
  // follows it must not count it a second time.
  let submitted = false

  function closeModal() {
    const el = document.getElementById(modalId)
    if (el) {
      // @ts-expect-error - DSFR is globally available
      window.dsfr(el).modal.conceal()
    }
  }

  function onSuccess() {
    submitted = true
    closeModal()
  }

  // "Plus tard", the close button, Escape and the backdrop all land here, and
  // all mean the same thing: the questions were shown and left blank. Sending
  // them blank is what counts the showing, so the re-ask delay and the cap on
  // showings apply to people who decline, not only to people who answer.
  // A signed-in account cannot leave a required question blank; the locked
  // popup asks for those.
  async function onClose() {
    if (submitted) {
      submitted = false
      return
    }
    const answers = survey.unansweredQuestions
      .filter((question) => !question.required || !auth.user)
      .map((question) => ({ question_id: question.id, value: null }))
    if (!answers.length) return

    try {
      await api.request('/survey/answers', {
        method: 'POST',
        body: JSON.stringify({ answers })
      })
      invalidate('survey:signup')
    } catch (err) {
      console.error(`Unable to record the dismissed survey: ${(err as Error).message}`)
    }
  }
</script>

{#if survey.showSurveyCard}
  <Modal
    id={modalId}
    titleId="form-{modalId}-title"
    sizeClass="fr-col-12 fr-col-md-8 fr-col-lg-6"
    teleport
    {onClose}
  >
    <SurveyForm
      id="form-{modalId}"
      title={m['survey.afterVote.title']()}
      description={m['survey.afterVote.description']()}
      onlyUnanswered
      dismissible
      {modalId}
      class="mt-5"
      {onSuccess}
    />
  </Modal>
{/if}
