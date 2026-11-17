<script lang="ts">
  import { Icon } from '$components/dsfr'

  let {
    icons,
    max = 3,
    count,
    fallbackIcon
  }: { icons: string[]; max?: number; count?: number | null; fallbackIcon: string } = $props()

  const displayed = $derived(icons.slice(0, max))
</script>

<div class="flex">
  {#each displayed as icon, i (i)}
    {@const iconProps = icon.startsWith('i-ri') ? { icon } : { src: icon, icon: fallbackIcon }}
    <div class="bg-white not-first:-ms-1 relative overflow-hidden rounded-full">
      <Icon {...iconProps} size="xs" block class="text-primary" />
    </div>
  {/each}
  {#if count !== null}
    <span class="ms-1 text-xs text-[--grey-625-425]">{count ?? icons.length}</span>
  {/if}
</div>
