<script lang="ts">
  import { Button, CheckboxGroup, Select } from '$components/dsfr'
  import type { MySurveyAnswer, MySurveyAnswersResponse } from '$lib/generated/backend'
  import { api } from '$lib/fastapi-client'
  import { getLocale } from '$lib/i18n/runtime'
  import { m } from '$lib/i18n/messages'
  import { useToast } from '$lib/helpers/useToast.svelte'
  import { onMount } from 'svelte'

  let loading = $state(true)
  let loadError = $state('')
  let saving = $state(false)
  let questions = $state<MySurveyAnswer[]>([])
  // One entry per question, keyed by question_id, holding whatever is
  // currently selected in the form, whatever its input type, so a select and
  // a checkbox group are edited and saved the same way.
  let selections = $state<Record<string, string[]>>({})

  onMount(load)

  async function load() {
    loading = true
    loadError = ''
    try {
      const locale = getLocale()
      const response = await api.request<MySurveyAnswersResponse>(
        `/survey/me?locale=${encodeURIComponent(locale)}`
      )
      questions = response.answers
      selections = Object.fromEntries(
        response.answers.map((answer) => [answer.question_id, [...answer.selected_keys]])
      )
    } catch {
      loadError = m['survey.profile.loadFailed']()
    } finally {
      loading = false
    }
  }

  function selectValue(questionId: string): string {
    return selections[questionId]?.[0] ?? ''
  }

  function setSelectValue(questionId: string, value: string) {
    selections[questionId] = value ? [value] : []
  }

  function clearAnswer(questionId: string) {
    selections[questionId] = []
  }

  async function save() {
    saving = true
    try {
      await api.request('/survey/answers', {
        method: 'POST',
        body: JSON.stringify({
          answers: questions.map((question) => ({
            question_id: question.question_id,
            option_keys: selections[question.question_id] ?? []
          }))
        })
      })
      useToast(m['survey.profile.saved'](), 4000, 'success')
    } catch {
      useToast(m['survey.profile.saveFailed'](), 6000, 'error')
    } finally {
      saving = false
    }
  }
</script>

{#if loading}
  <section class="fr-mt-8v" aria-labelledby="survey-answers-title">
    <h2 id="survey-answers-title" class="fr-h4">{m['survey.profile.title']()}</h2>
    <p role="status">{m['survey.profile.loading']()}</p>
  </section>
{:else if loadError}
  <section class="fr-mt-8v" aria-labelledby="survey-answers-title">
    <h2 id="survey-answers-title" class="fr-h4">{m['survey.profile.title']()}</h2>
    <p class="fr-error-text" role="alert">{loadError}</p>
  </section>
{:else if questions.length > 0}
  <section class="fr-mt-8v" aria-labelledby="survey-answers-title">
    <h2 id="survey-answers-title" class="fr-h4">{m['survey.profile.title']()}</h2>
    <p class="fr-text--sm text-grey max-w-[800px]">{m['survey.profile.description']()}</p>

    <div class="gap-6 flex max-w-[500px] flex-col">
      {#each questions as question (question.question_id)}
        {#if question.input_type === 'select'}
          <Select
            id="survey-answer-{question.question_id}"
            label={question.label}
            bind:selected={
              () => selectValue(question.question_id),
              (value) => setSelectValue(question.question_id, value)
            }
            options={[
              { value: '', label: m['survey.profile.noAnswerOption']() },
              ...question.options.map((option) => ({ value: option.key, label: option.label }))
            ]}
          />
        {:else}
          <CheckboxGroup
            id="survey-answer-{question.question_id}"
            legend={question.label}
            options={question.options.map((option) => ({
              value: option.key,
              label: option.label
            }))}
            bind:value={selections[question.question_id]}
          />
        {/if}
        {#if (selections[question.question_id]?.length ?? 0) > 0}
          <Button
            variant="tertiary"
            size="sm"
            text={m['survey.profile.clear']()}
            onclick={() => clearAnswer(question.question_id)}
          />
        {/if}
      {/each}
    </div>

    <Button
      class="fr-mt-4v"
      text={saving ? m['survey.profile.saving']() : m['words.save']()}
      disabled={saving}
      onclick={save}
    />
  </section>
{/if}
