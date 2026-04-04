<script lang="ts">
  let {
    pos,
    name,
    description,
    duration_ms,
    error,
    selected
  }: {
    pos: string
    name: string
    description: string
    duration_ms: number
    error: string | null
    selected: boolean
  } = $props()

  const durationLabel = $derived(
    duration_ms >= 1000
      ? `${(duration_ms / 1000).toFixed(1)}s`
      : `${duration_ms}ms`
  )
</script>

<div
  class="cg-border rounded-lg bg-white p-4 md:p-6 flex flex-col gap-3 {selected ? 'border-green-500 border-2' : ''}"
>
  <div class="flex items-center gap-2">
    <div class="c-bot-disk-{pos.toLowerCase()}"></div>
    <p class="mb-0! font-bold">Tool {pos.toUpperCase()}</p>
    {#if selected}
      <span class="ml-auto px-3 py-1 rounded-full bg-green-100 text-green-700 text-sm font-bold border border-green-300">
        Winner
      </span>
    {/if}
  </div>

  <div>
    <h5 class="text-base font-bold text-dark-grey mb-1">{name}</h5>
    <p class="text-sm text-grey mb-0!">{description}</p>
  </div>

  {#if error}
    <div class="rounded bg-red-50 border border-red-200 p-3">
      <p class="text-xs text-red-700 mb-0!">Error: {error}</p>
    </div>
  {:else}
    <div class="flex items-center gap-2 text-sm text-grey">
      <span class="font-medium">Response time:</span>
      <span class="font-bold text-dark-grey">{durationLabel}</span>
    </div>
  {/if}
</div>
