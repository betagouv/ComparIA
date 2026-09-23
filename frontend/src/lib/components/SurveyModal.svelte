<script lang="ts">
  import { Button, Modal } from '$components/dsfr'
  import Form from '$components/form/Form.svelte'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import {
    answersToForm,
    formToAnswers,
    getSurveyContext,
    hasShownSurveyThisSession,
    markSurveyShownThisSession,
    questionsToFormItems
  } from '$lib/survey'

  const modalId = 'fr-modal-survey'
  const survey = getSurveyContext()
  // Decided once, when the popup mounts: whether there is anything to ask and
  // whether this visitor has already been offered the popup this session.
  const shouldOpen = !!survey.voteQuestions?.length && !hasShownSurveyThisSession()

  const items = $derived(questionsToFormItems(survey.voteQuestions!))
  const form = $derived(answersToForm([], survey.voteQuestions!))

  // Long enough for the visitor to read the reveal they just asked for before
  // a popup lands on it, short enough that they are still on the page.
  const OPEN_DELAY_MS = 1000

  // The DSFR modal script discloses on a change of data-fr-opened, not on its
  // initial value, so the attribute has to start false and flip once DSFR has
  // registered the button.
  let opened = $state(false)
  $effect(() => {
    const timer = setTimeout(() => {
      // Marked here rather than on mount: a visitor who leaves during the
      // delay never saw the popup, so it should still be waiting for them.
      if (shouldOpen) {
        markSurveyShownThisSession()
        void recordShown()
      }
      opened = shouldOpen
    }, OPEN_DELAY_MS)
    return () => clearTimeout(timer)
  })

  // Every question counts as shown the moment the popup lands, whatever the
  // visitor does next: closing it, answering, or leaving the page with it
  // open. Counting on close only would let the last of these ask forever.
  async function recordShown() {
    try {
      await api.request('/survey/dismiss', {
        method: 'POST',
        body: JSON.stringify({ question_ids: survey.voteQuestions!.map((q) => q.id) })
      })
    } catch (error) {
      console.error(`Unable to record survey showing: ${(error as Error).message}`)
    }
  }

  // Guards the popup from saving the same answers twice, e.g. Escape and a
  // click both firing onClose, or a double click on submit.
  let handled = $state(false)
  let submitFailed = $state(false)

  // Whatever was selected goes to /survey/answers. The showing itself was
  // recorded when the popup opened. Returns whether everything was saved.
  async function saveAnswers(): Promise<boolean> {
    const updatedAnswers = formToAnswers(form, survey.voteQuestions!, true)

    try {
      if (updatedAnswers.length > 0) {
        await api.request('/survey/answers', {
          method: 'POST',
          body: JSON.stringify({ answers: updatedAnswers })
        })
      }
      submitFailed = false
      return true
    } catch (error) {
      console.error(`Unable to record survey response: ${(error as Error).message}`)
      submitFailed = true
      return false
    }
  }

  // Closing the popup without submitting declines the questions left blank.
  // Selections that exist are real answers and go through the same path as a
  // submit. There is exactly one save per popup, whichever of close or submit
  // fires first.
  function onClose() {
    if (handled) return
    handled = true
    void saveAnswers()
  }

  // Deliberately not wired to aria-controls: DSFR closes the modal on its own
  // click listener, and the close reaches onClose before this handler would
  // run, so onClose would win the `handled` race and throw the answers away.
  // Record first, then close by flipping the attribute back, and stay open
  // with an error notice when recording fails, so nothing is lost silently.
  async function onSubmit() {
    if (handled) return
    handled = true
    if (await saveAnswers()) {
      opened = false
    } else {
      // Let the visitor retry: the next submit or close records again.
      handled = false
    }
  }
</script>

{#if shouldOpen}
  <!-- Opened programmatically, not by a visible trigger: this hidden button
       is what tells the DSFR modal script to disclose it once, on mount. -->
  <button class="hidden" data-fr-opened={opened} aria-controls={modalId}>Hidden</button>

  <Modal
    id={modalId}
    titleId="form-{modalId}-title"
    sizeClass="fr-col-12 fr-col-md-8 fr-col-lg-6"
    {onClose}
  >
    <Form
      id="form-{modalId}"
      label={m['survey.afterVote.title']()}
      description={m['survey.afterVote.description']()}
      {items}
      {form}
      {onSubmit}
    >
      {#snippet errorSnippet()}
        {#if submitFailed}
          <p class="fr-error-text" role="alert">{m['survey.afterVote.submitFailed']()}</p>
        {/if}
      {/snippet}

      {#snippet btnSnippet()}
        <div class="gap-3 flex flex-wrap items-center justify-end">
          <Button
            variant="tertiary-no-outline"
            text={m['survey.afterVote.dismiss']()}
            aria-controls={modalId}
          />
          <Button type="submit" text={m['survey.afterVote.submit']()} />
        </div>
      {/snippet}
    </Form>
  </Modal>
{/if}
