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

<div class="cg-border gap-4 rounded-lg! bg-white p-4 md:rounded-lg md:px-6 md:py-8 flex w-full flex-col">
  <div class="flex items-center">
    <div class="c-bot-disk-{label.toLowerCase()}"></div>
    <p class="ms-1! mb-0! font-bold">Tool {label}</p>
  </div>

  {#if loading}
    <div class="py-6">
      <p class="fr-text--sm text-grey animate-pulse mb-0!">Comparing...</p>
    </div>
  {:else if error}
    <div class="cg-border rounded-lg! p-4 bg-very-light-grey">
      <p class="fr-text--sm text-grey italic mb-0!">Tool encountered an error</p>
    </div>
  {:else if result}
    <div class="fr-text--sm text-dark-grey whitespace-pre-wrap">{result}</div>
  {:else}
    <div class="py-6">
      <p class="fr-text--sm text-grey mb-0!">No result</p>
    </div>
  {/if}
</div>
