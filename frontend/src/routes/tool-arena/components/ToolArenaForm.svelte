<script lang="ts">
  let {
    onsubmit,
    disabled = false
  }: {
    onsubmit: (task: string, goal: string) => void
    disabled?: boolean
  } = $props()

  let task = $state('')
  let goal = $state('')

  const canSubmit = $derived(task.trim().length > 0 && goal.trim().length > 0 && !disabled)

  function handleSubmit(e: SubmitEvent) {
    e.preventDefault()
    if (canSubmit) {
      onsubmit(task.trim(), goal.trim())
    }
  }
</script>

<form class="fr-container" onsubmit={handleSubmit}>
  <div class="mb-6">
    <label for="tool-arena-task" class="mb-2 block font-bold text-dark-grey">
      Task
      <span class="text-sm font-normal text-grey ml-1">What should the tool do?</span>
    </label>
    <textarea
      id="tool-arena-task"
      class="w-full rounded border p-3 min-h-[80px] resize-y focus:outline-none focus:ring-2 focus:ring-primary"
      placeholder="e.g. Summarize this article: ..."
      bind:value={task}
      {disabled}
      required
    ></textarea>
  </div>

  <div class="mb-8">
    <label for="tool-arena-goal" class="mb-2 block font-bold text-dark-grey">
      Goal
      <span class="text-sm font-normal text-grey ml-1">What does a good result look like?</span>
    </label>
    <textarea
      id="tool-arena-goal"
      class="w-full rounded border p-3 min-h-[80px] resize-y focus:outline-none focus:ring-2 focus:ring-primary"
      placeholder="e.g. A concise 3-sentence summary covering the main points"
      bind:value={goal}
      {disabled}
      required
    ></textarea>
  </div>

  <div class="text-center">
    <button
      type="submit"
      class="px-8 py-3 rounded-lg bg-primary text-white font-bold hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      disabled={!canSubmit}
    >
      Compare Tools
    </button>
  </div>
</form>
