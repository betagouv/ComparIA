<script lang="ts">
  import { invalidate } from '$app/navigation'
  import Form from '$lib/components/form/Form.svelte'
  import { api } from '$lib/fastapi-client'
  import type {
    MySurveyAnswer,
    PublicSurveyQuestion,
    SurveyQuestionAnswer
  } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import { answersToForm, formToAnswers, questionsToFormItems, requiredErrors } from '$lib/survey'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    id,
    title,
    description,
    questions,
    answers,
    onSuccess,
    ...props
  }: Omit<SvelteHTMLElements['form'], 'method'> & {
    id: string
    title: string
    description?: string
    questions: PublicSurveyQuestion[]
    answers: MySurveyAnswer[]
    onSuccess?: (form: SurveyQuestionAnswer[]) => void
  } = $props()

  let items = $derived(questionsToFormItems(questions))
  let form = $derived(answersToForm(answers, questions))
  let errors = $state<Record<string, string>>({})
  let failed = $state(false)

  async function onBeforeSubmit() {
    failed = false
    // Checked here rather than left to the browser: a group of checkboxes has
    // no native 'at least one' constraint, and a required question sent blank
    // would let the form close while the arena keeps refusing every write.
    errors = requiredErrors(form, questions)
    if (Object.keys(errors).length) return false

    // Blank questions are sent too: an empty list is how an answer is cleared,
    // and on a question never answered it changes nothing.
    const updatedAnswers = formToAnswers(form, questions)

    try {
      await api.request('/survey/answers', {
        method: 'POST',
        body: JSON.stringify({ answers: updatedAnswers })
      })
      invalidate('survey:signup')
      onSuccess?.(updatedAnswers)
    } catch (err) {
      console.error(`Unable to save signup survey answers: ${(err as Error).message}`)
      failed = true
      return false
    }
  }
</script>

<Form
  {...props}
  {id}
  label={title}
  {description}
  {items}
  {form}
  bind:errors
  onSubmit={onBeforeSubmit}
>
  {#snippet errorSnippet()}
    {#if failed}
      <p class="fr-error-text" role="alert">{m['survey.afterVote.submitFailed']()}</p>
    {/if}
  {/snippet}
</Form>
