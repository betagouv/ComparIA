<script lang="ts">
  import type { EnergyClass } from '$lib/mockModelExtras'

  let { value }: { value: EnergyClass } = $props()

  // EU energy-label palette, A (efficient) → F (least efficient). Widths are
  // percentages of the tile so the label scales to fill its box; the classic
  // stepped silhouette (A short → F long) is preserved. The right edge is left
  // free for the active-class marker.
  const rows: { c: EnergyClass; color: string; width: number }[] = [
    { c: 'A', color: '#00963a', width: 46 },
    { c: 'B', color: '#4fb648', width: 55 },
    { c: 'C', color: '#bdd732', width: 64 },
    { c: 'D', color: '#ffec00', width: 73 },
    { c: 'E', color: '#f9a01b', width: 82 },
    { c: 'F', color: '#e30613', width: 91 }
  ]
</script>

<div class="flex w-full flex-col gap-[5px]" aria-label="Classe de consommation énergétique {value}">
  {#each rows as row (row.c)}
    {@const active = row.c === value}
    <div class="relative flex h-[22px] items-center">
      <div
        class="flex h-full items-center justify-start ps-2 text-sm font-bold text-white"
        style="background-color: {row.color}; width: {row.width}%; clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 50%, calc(100% - 10px) 100%, 0 100%);"
        class:opacity-30={!active}
      >
        {row.c}
      </div>
      {#if active}
        <div class="absolute right-0 flex items-center leading-none">
          <span class="text-xs text-black">◀</span>
          <span class="ms-[-2px] rounded-sm bg-black px-2 py-[3px] text-sm font-bold text-white">
            {row.c}
          </span>
        </div>
      {/if}
    </div>
  {/each}
</div>
