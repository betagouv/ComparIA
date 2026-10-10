<script lang="ts">
  import { Button, Modal } from '$components/dsfr'
  import Form from '$components/form/Form.svelte'
  import { api } from '$lib/fastapi-client'
  import { m } from '$lib/i18n/messages'
  import { getCohortContext } from '$lib/stores/cohortStore.svelte'
  import {
    answersToForm,
    formToAnswers,
    getSurveyContext,
    questionsToFormItems
  } from '$lib/survey.svelte'

  const modalId = 'fr-modal-survey'
  const survey = getSurveyContext()
  const cohorts = getCohortContext()
  // Decided once, when the popup mounts: whether there is anything to ask and
  // whether this visitor has already been offered the popup this session.
  // FIXME hardcoded: do not show survey for 'pix' cohorts
  const shouldOpen = cohorts !== 'pix' && !!survey.questions?.length

  // Nothing is required here, whatever the question says: 'required' only
  // holds up the signup form, and this popup is optional by design.
  const items = $derived(
    questionsToFormItems(survey.questions!.map((q) => ({ ...q, required: false })))
  )
  const form = $derived(answersToForm([], survey.questions!))
  let submitFailed = $state(false)

  // The DSFR modal script discloses on a change of data-fr-opened, not on its
  // initial value, so the attribute has to start false and flip once DSFR has
  // registered the button.
  let opened = $state(false)

  async function saveAnswers(): Promise<void> {
    const updatedAnswers = formToAnswers(form, survey.questions!, true)
    submitFailed = false

    try {
      if (updatedAnswers.length > 0) {
        await api.request('/survey/answers', {
          method: 'POST',
          body: JSON.stringify({ answers: updatedAnswers })
        })
      }
      opened = false
    } catch (error) {
      console.error(`Unable to record survey response: ${(error as Error).message}`)
      submitFailed = true
    }
  }
</script>

{#if shouldOpen}
  <!-- Opened programmatically, not by a visible trigger: this hidden button
       is what tells the DSFR modal script to disclose it once, on mount. -->
  <button class="hidden" data-fr-opened={opened} aria-controls={modalId}>Hidden</button>

  <Modal id={modalId} titleId="form-{modalId}-title" sizeClass="fr-col-12 fr-col-md-8 fr-col-lg-6">
    <Form
      id="form-{modalId}"
      label={m['survey.afterVote.title']()}
      description={m['survey.afterVote.description']()}
      {items}
      {form}
      onSubmit={saveAnswers}
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
