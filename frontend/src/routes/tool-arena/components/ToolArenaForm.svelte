<script lang="ts">
  import { Button } from '$components/dsfr'
  import { m } from '$lib/i18n/messages'

  let {
    onsubmit,
    disabled = false
  }: {
    onsubmit: (task: string, goal: string, documentContent: string) => void
    disabled?: boolean
  } = $props()

  const taskTypes = [
    { value: 'summarize', label: m['toolArena.form.taskTypes.summarize.label'](), prompt: m['toolArena.form.taskTypes.summarize.prompt'](), goalText: m['toolArena.form.taskTypes.summarize.goal']() }
  ]

  let selectedTaskType = $state(taskTypes[0].value)
  let task = $state(taskTypes[0].prompt)
  let goal = $state(taskTypes[0].goalText)
  let documentContent = $state('')
  let fileName = $state('')
  let fileError = $state('')

  const requiresDocument = $derived(selectedTaskType === 'summarize')

  const canSubmit = $derived(
    task.trim().length > 0 &&
    goal.trim().length > 0 &&
    (!requiresDocument || documentContent.trim().length > 0) &&
    !disabled
  )

  function handleSubmit(e: SubmitEvent) {
    e.preventDefault()
    if (canSubmit) {
      onsubmit(task.trim(), goal.trim(), documentContent)
    }
  }

  function handleTaskTypeChange() {
    const selected = taskTypes.find(t => t.value === selectedTaskType)
    if (selected) {
      task = selected.prompt
      goal = selected.goalText
    }
  }

  function handleFileChange(e: Event) {
    const input = e.target as HTMLInputElement
    const file = input.files?.[0]
    fileError = ''
    if (!file) {
      documentContent = ''
      fileName = ''
      return
    }
    if (file.size > 500_000) {
      fileError = 'Le fichier est trop volumineux (max 500 Ko).'
      documentContent = ''
      fileName = ''
      return
    }
    fileName = file.name
    const reader = new FileReader()
    reader.onload = (ev) => {
      documentContent = (ev.target?.result as string) ?? ''
    }
    reader.onerror = () => {
      fileError = 'Impossible de lire le fichier.'
      documentContent = ''
    }
    reader.readAsText(file)
  }

  const suggestions = [
    { icon: 'fr-icon-file-text-line', text: m['toolArena.form.suggestions.1.text']() },
    { icon: 'fr-icon-bar-chart-box-line', text: m['toolArena.form.suggestions.2.text']() },
    { icon: 'fr-icon-search-line', text: m['toolArena.form.suggestions.3.text']() },
    { icon: 'fr-icon-question-line', text: m['toolArena.form.suggestions.4.text']() }
  ]
</script>

<form onsubmit={handleSubmit} class="gap-3 py-10 md:pb-12 md:pt-12 grid">
  <div class="fr-select-group">
    <label class="fr-label" for="tool-arena-task-type">
      Type de tâche
    </label>
    <select
      id="tool-arena-task-type"
      class="fr-select"
      bind:value={selectedTaskType}
      onchange={handleTaskTypeChange}
      {disabled}
    >
      {#each taskTypes as taskType}
        <option value={taskType.value}>{taskType.label}</option>
      {/each}
    </select>
  </div>

  {#if requiresDocument}
    <div class="fr-upload-group" class:fr-upload-group--error={!!fileError}>
      <label class="fr-label" for="tool-arena-document">
        Document à analyser
        <span class="fr-hint-text">Formats acceptés : .txt, .md — Taille max : 500 Ko</span>
      </label>
      <input
        id="tool-arena-document"
        class="fr-upload"
        type="file"
        accept=".txt,.md"
        onchange={handleFileChange}
        {disabled}
      />
      {#if fileError}
        <p class="fr-error-text">{fileError}</p>
      {/if}
      {#if fileName && !fileError}
        <p class="fr-valid-text">{fileName} chargé avec succès</p>
      {/if}
    </div>
  {/if}

  <div class="fr-input-group">
    <label class="fr-label hidden!" for="tool-arena-task">Task</label>
    <textarea
      id="tool-arena-task"
      class="fr-input cg-border rounded-t-md! bg-white! rounded-b-none! border-solid!"
      rows="4"
      bind:value={task}
      placeholder={m['toolArena.form.taskPlaceholder']()}
      {disabled}
    ></textarea>
  </div>

  <div class="gap-3 md:grid-flow-row-dense md:grid-cols-6 grid">
    <div class="fr-input-group md:col-span-4">
      <label class="fr-label hidden!" for="tool-arena-goal">Goal</label>
      <input
        id="tool-arena-goal"
        type="text"
        class="fr-input cg-border rounded-md! bg-white! border-solid!"
        bind:value={goal}
        placeholder={m['toolArena.form.goalPlaceholder']()}
        {disabled}
      />
    </div>

    <div class="md:col-span-2 flex justify-end items-start">
      <Button type="submit" disabled={!canSubmit}>
        {m['toolArena.form.submit']()}
      </Button>
    </div>
  </div>
</form>

<div class="mt-2">
  <p class="font-bold mb-4">Suggestions</p>
  <div class="gap-4 md:grid-cols-4 grid grid-cols-2">
    {#each suggestions as suggestion}
      <button
        type="button"
        class="cg-border rounded-lg! bg-white p-4 text-left hover:bg-light-grey transition-colors cursor-pointer flex flex-col gap-3"
        onclick={(e) => {
          e.preventDefault()
          task = suggestion.text
          goal = m['toolArena.form.taskTypes.summarize.goal']()
        }}
      >
        <span class={['text-primary text-xl', suggestion.icon]} aria-hidden="true"></span>
        <span class="fr-text--sm text-dark-grey">{suggestion.text}</span>
      </button>
    {/each}
  </div>
</div>

<style lang="postcss">
  .fr-input {
    --border-plain-grey: var(--blue-france-main-525);
  }
</style>
