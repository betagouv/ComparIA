<script lang="ts">
  import type { Tier } from '$lib/mockModelExtras'

  let { value }: { value: Tier } = $props()

  // Categorical tier colors (matching the leaderboard) — identity, not a good→bad
  // gradient, to avoid implying a low tier means a "bad" model.
  const tiers: { c: Tier; color: string }[] = [
    { c: 'I', color: '#6a6af4' },
    { c: 'II', color: '#1f9d6d' },
    { c: 'III', color: '#a96afe' },
    { c: 'IV', color: '#e8830c' },
    { c: 'V', color: '#d6336c' }
  ]
</script>

<div class="flex gap-2" role="img" aria-label="Niveau {value} sur 5">
  {#each tiers as t (t.c)}
    {@const active = t.c === value}
    <div
      class={[
        'flex h-9 flex-1 items-center justify-center rounded-lg border-2 text-base font-bold',
        active ? 'shadow-sm' : 'border-[--grey-925-125] text-grey'
      ]}
      style={active ? `color:${t.color}; border-color:${t.color}; background-color:${t.color}1f;` : ''}
    >
      {t.c}
    </div>
  {/each}
</div>
