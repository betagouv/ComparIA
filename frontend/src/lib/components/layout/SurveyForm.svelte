<script lang="ts">
  import { invalidate } from '$app/navigation'
  import { Button } from '$components/dsfr'
  import Form from '$lib/components/form/Form.svelte'
  import { api } from '$lib/fastapi-client'
  import type { SurveyQuestionAnswer } from '$lib/generated/backend'
  import { m } from '$lib/i18n/messages'
  import {
    answersToForm,
    getSurveyContext,
    profileQuestions,
    questionsToFormItems,
    requiredErrors
  } from '$lib/survey.svelte'
  import type { SvelteHTMLElements } from 'svelte/elements'

  let {
    id,
    title,
    description,
    onlyUnanswered = false,
    dismissible = false,
    modalId,
    onSuccess,
    ...props
  }: Omit<SvelteHTMLElements['form'], 'method'> & {
    id: string
    title: string
    description?: string
    onlyUnanswered?: boolean
    dismissible?: boolean
    modalId?: string
    onSuccess?: (form: SurveyQuestionAnswer[]) => void
  } = $props()

  const survey = getSurveyContext()
  const questions = $derived(
    onlyUnanswered ? survey.unansweredQuestions : profileQuestions(survey.questions, survey.answers)
  )
  let items = $derived(questionsToFormItems(questions, dismissible))
  let form = $derived(answersToForm(survey.answers, questions))
  let errors = $state<Record<string, string>>({})
  let failed = $state(false)

  function sameValue(a: string | string[] | null, b: string | string[] | null) {
    const normalize = (value: string | string[] | null) =>
      Array.isArray(value) ? (value.length ? [...value].sort().join('\n') : null) : value || null
    return normalize(a) === normalize(b)
  }

  async function onBeforeSubmit() {
    failed = false
    // Checked here rather than left to the browser: a group of checkboxes has
    // no native 'at least one' constraint, and a required question sent blank
    // would let the form close while the arena keeps refusing every write.
    errors = requiredErrors(form, items)
    if (Object.keys(errors).length) return false

    // The backend counts a blank question as one showing of it. In the popup
    // that is the point: every question was put to the person. On the profile
    // page it is not, so only the questions the person changed are sent, and
    // a blank one there means an answer cleared.
    const saved = answersToForm(survey.answers, questions)
    const updatedAnswers = questions
      .filter((field) => onlyUnanswered || !sameValue(form[field.id], saved[field.id]))
      .map((field) => ({
        question_id: field.id,
        value: form[field.id]
      }))

    if (!updatedAnswers.length) {
      onSuccess?.(updatedAnswers)
      return
    }

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

  {#snippet btnSnippet()}
    <div class="gap-3 flex flex-wrap items-center justify-end">
      {#if dismissible && modalId}
        <Button
          variant="tertiary-no-outline"
          text={m['survey.afterVote.dismiss']()}
          aria-controls={modalId}
        />
      {/if}
      <Button type="submit" text={m['survey.afterVote.submit']()} />
    </div>
  {/snippet}
</Form>
