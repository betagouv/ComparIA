<script lang="ts">
  import { Badge } from '$components/dsfr'

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
  class="cg-border gap-4 rounded-lg! bg-white p-4 md:rounded-lg md:px-6 md:py-8 flex w-full flex-col"
  class:border-blue-france={selected}
>
  <div class="flex items-center justify-between">
    <div class="flex items-center">
      <div class="c-bot-disk-{pos}"></div>
      <p class="ms-1! mb-0! font-bold">Tool {pos.toUpperCase()}</p>
    </div>
    {#if selected}
      <Badge small type="success">Winner</Badge>
    {/if}
  </div>

  <div>
    <p class="mb-1! font-bold text-dark-grey">{name}</p>
    <p class="fr-text--sm text-grey mb-0!">{description}</p>
  </div>

  <div class="flex items-center gap-2 mt-auto">
    {#if error}
      <Badge small type="error">Error</Badge>
    {:else}
      <Badge small type="info">{durationLabel}</Badge>
    {/if}
  </div>
</div>

<style>
  .border-blue-france {
    border: 2px solid var(--blue-france-main-525);
  }
</style>
