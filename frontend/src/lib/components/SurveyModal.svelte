<script lang="ts">
  import { Button, Modal } from '$components/dsfr'
  import SurveyQuestionField from '$lib/components/SurveyQuestionField.svelte'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import {
    getSurveyQuestionsContext,
    hasShownSurveyThisSession,
    markSurveyShownThisSession
  } from '$lib/survey'

  const modalId = 'fr-modal-survey'
  const questions = getSurveyQuestionsContext()

  // Decided once, when the popup mounts: whether there is anything to ask and
  // whether this visitor has already been offered the popup this session.
  const show = questions.length > 0 && !hasShownSurveyThisSession()

  // Long enough for the visitor to read the reveal they just asked for before
  // a popup lands on it, short enough that they are still on the page.
  const OPEN_DELAY_MS = 4000

  // The DSFR modal script discloses on a change of data-fr-opened, not on its
  // initial value, so the attribute has to start false and flip once DSFR has
  // registered the button.
  let opened = $state(false)
  $effect(() => {
    const timer = setTimeout(() => {
      // Marked here rather than on mount: a visitor who leaves during the
      // delay never saw the popup, so it should still be waiting for them.
      if (show) markSurveyShownThisSession()
      opened = show
    }, OPEN_DELAY_MS)
    return () => clearTimeout(timer)
  })

  let answers = $state<Record<string, string[]>>(
    Object.fromEntries(questions.map((question) => [question.id, []]))
  )

  // Guards the popup from recording the same showing twice, e.g. Escape and a
  // click both firing onClose, or a double click on submit. A double-fire
  // would burn one of the visitor's three chances to be asked again for
  // nothing.
  let handled = $state(false)
  let submitFailed = $state(false)

  // One recording pass for the whole popup: whatever was selected goes to
  // /survey/answers, whatever was left blank counts as shown-and-declined.
  // Returns whether everything was recorded.
  async function recordShowing(): Promise<boolean> {
    const answered = questions
      .map((question) => ({ question_id: question.id, option_keys: answers[question.id] ?? [] }))
      .filter((answer) => answer.option_keys.length > 0)
    // Left blank in a popup the visitor otherwise submitted: still shown, so
    // it still counts against the re-ask limit.
    const blankIds = questions
      .filter((question) => (answers[question.id] ?? []).length === 0)
      .map((question) => question.id)

    try {
      if (answered.length > 0) {
        await api.request('/survey/answers', {
          method: 'POST',
          body: JSON.stringify({ answers: answered })
        })
      }
      if (blankIds.length > 0) {
        await api.request('/survey/dismiss', {
          method: 'POST',
          body: JSON.stringify({ question_ids: blankIds })
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

  // Closing the popup without submitting is declining on purpose, but only
  // for the questions left blank. Selections that exist are real answers and
  // go through the same path as a submit; only blanks are recorded as
  // dismissed. There is exactly one recording pass per popup, whichever of
  // close or submit fires first.
  function onClose() {
    if (handled) return
    handled = true
    void recordShowing()
  }

  // Deliberately not wired to aria-controls: DSFR closes the modal on its own
  // click listener, and the close reaches onClose before this handler would
  // run, so onClose would win the `handled` race and throw the answers away.
  // Record first, then close by flipping the attribute back, and stay open
  // with an error notice when recording fails, so nothing is lost silently.
  async function onSubmit() {
    if (handled) return
    handled = true
    if (await recordShowing()) {
      opened = false
    } else {
      // Let the visitor retry: the next submit or close records again.
      handled = false
    }
  }
</script>

{#if show}
  <!-- Opened programmatically, not by a visible trigger: this hidden button
       is what tells the DSFR modal script to disclose it once, on mount. -->
  <button class="hidden" data-fr-opened={opened} aria-controls={modalId}>Hidden</button>

  <Modal
    id={modalId}
    titleId="{modalId}-title"
    sizeClass="fr-col-12 fr-col-md-8 fr-col-lg-6"
    {onClose}
  >
    <h2 id="{modalId}-title" class="fr-modal__title text-primary!">
      {m['survey.afterVote.title']()}
    </h2>
    <p class="text-sm! text-grey mb-6!">{m['survey.afterVote.description']()}</p>

    <div class="mb-8 flex flex-col">
      {#each questions as question (question.id)}
        <SurveyQuestionField
          {question}
          onchange={(option_keys) => (answers[question.id] = option_keys)}
        />
      {/each}
    </div>

    {#if submitFailed}
      <p class="fr-error-text" role="alert">{m['survey.afterVote.submitFailed']()}</p>
    {/if}

    <div class="gap-3 flex flex-wrap items-center justify-end">
      <Button
        variant="tertiary-no-outline"
        text={m['survey.afterVote.dismiss']()}
        aria-controls={modalId}
      />
      <Button text={m['survey.afterVote.submit']()} onclick={onSubmit} />
    </div>
  </Modal>
{/if}
