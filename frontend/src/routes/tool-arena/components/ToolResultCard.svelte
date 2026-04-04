<script lang="ts">
  let {
    label,
    result,
    error,
    loading = false
  }: {
    label: string
    result: string | null
    error: string | null
    loading?: boolean
  } = $props()
</script>

<div class="cg-border rounded-lg bg-white p-4 md:p-6 flex flex-col gap-3">
  <div class="flex items-center gap-2">
    <div class="c-bot-disk-{label.toLowerCase()}"></div>
    <p class="mb-0! font-bold">Tool {label}</p>
  </div>

  {#if loading}
    <div class="py-8 text-center text-grey">
      <p class="text-sm animate-pulse">Loading result...</p>
    </div>
  {:else if error}
    <div class="rounded bg-red-50 border border-red-200 p-4">
      <p class="text-sm text-red-700 mb-0!">Tool encountered an error</p>
      <p class="text-xs text-red-500 mt-1 mb-0!">{error}</p>
    </div>
  {:else if result}
    <div class="text-sm leading-relaxed whitespace-pre-wrap text-dark-grey">
      {result}
    </div>
  {:else}
    <div class="py-8 text-center text-grey">
      <p class="text-sm">No result</p>
    </div>
  {/if}
</div>
