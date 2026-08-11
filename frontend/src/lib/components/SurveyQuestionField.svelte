<script lang="ts">
  import { CheckboxGroup, Select } from '$components/dsfr'

  export type SurveyOption = { key: string; label: string }
  export type SurveyQuestion = {
    id: string
    key: string
    trigger: string
    input_type: 'select' | 'checkbox_group'
    label: string
    revision: number
    options: SurveyOption[]
  }

  let {
    question,
    value = [],
    placeholder = '',
    disabled = false,
    onchange
  }: {
    question: SurveyQuestion
    value?: string[]
    placeholder?: string
    disabled?: boolean
    onchange: (option_keys: string[]) => void
  } = $props()

  // Local, uncontrolled after mount: the DSFR inputs need a real bindable
  // variable, not a read of the `value` prop, so the initial answer seeds it
  // once and every further change is reported upward through `onchange`.
  let selectedKey = $state(value[0] ?? '')
  let selectedKeys = $state<string[]>([...value])

  const selectOptions = $derived([
    { value: '', label: placeholder },
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
    label={question.label}
    onchange={onSelectChange}
    {disabled}
    class="mb-4!"
  />
{:else}
  <CheckboxGroup
    id="survey-question-{question.id}"
    bind:value={selectedKeys}
    options={checkboxOptions}
    legend={question.label}
    {disabled}
    class="mb-4!"
  />
{/if}
