<script lang="ts">
  import { CheckboxGroup, Select } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'

  export type SurveyOption = { key: string; label: string }
  export type SurveyQuestion = {
    id: string
    key: string
    required: boolean
    input_type: 'select' | 'checkbox_group'
    label: string
    revision: number
    options: SurveyOption[]
  }

  let {
    question,
    value = [],
    placeholder = '',
    optionalSuffix = '',
    disabled = false,
    onchange
  }: {
    question: SurveyQuestion
    value?: string[]
    placeholder?: string
    // Appended to the label of a question that may be left blank. Empty
    // where every question is optional anyway, like the after-vote popup:
    // saying so on each one there says nothing.
    optionalSuffix?: string
    disabled?: boolean
    onchange: (option_keys: string[]) => void
  } = $props()

  const label = $derived(question.required ? question.label : question.label + optionalSuffix)

  // Local, uncontrolled after mount: the DSFR inputs need a real bindable
  // variable, not a read of the `value` prop, so the initial answer seeds it
  // once and every further change is reported upward through `onchange`.
  let selectedKey = $state(value[0] ?? '')
  let selectedKeys = $state<string[]>([...value])

  // The blank first entry of a select needs a visible, spoken label: an empty
  // one reads as a broken control. Required questions ask to be answered,
  // optional ones offer the explicit way out.
  const emptyOptionLabel = $derived(
    placeholder ||
      (question.required
        ? m['survey.question.chooseOption']()
        : m['survey.profile.noAnswerOption']())
  )
  const selectOptions = $derived([
    { value: '', label: emptyOptionLabel },
    ...question.options.map((option) => ({ value: option.key, label: option.label }))
  ])
  const checkboxOptions = $derived(
    question.options.map((option) => ({ value: option.key, label: option.label }))
  )

  function onSelectChange() {
    onchange(selectedKey ? [selectedKey] : [])
  }

  $effect(() => {
    // CheckboxGroup only exposes a bindable value, no change callback, so the
    // group's answer is reported whenever it changes rather than on a single
    // event.
    if (question.input_type === 'checkbox_group') onchange(selectedKeys)
  })
</script>

{#if question.input_type === 'select'}
  <Select
    id="survey-question-{question.id}"
    bind:selected={selectedKey}
    options={selectOptions}
    {label}
    onchange={onSelectChange}
    {disabled}
    aria-required={question.required || undefined}
    class="mb-4!"
  />
{:else}
  <CheckboxGroup
    id="survey-question-{question.id}"
    bind:value={selectedKeys}
    options={checkboxOptions}
    legend={label}
    {disabled}
    class="mb-4!"
  />
{/if}
